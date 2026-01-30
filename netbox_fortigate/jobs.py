from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from netbox.jobs import JobRunner

from .models import FortiGateScheduler, FortiGateDevice
from .choices import ScheduleFrequencyChoices, ScheduleModeChoices


# =========================
# CRON COMPUTATION
# =========================

@dataclass(frozen=True)
class NextRun:
    dt: datetime


def _aware(dt: datetime) -> datetime:
    tz = timezone.get_current_timezone()
    return dt if timezone.is_aware(dt) else timezone.make_aware(dt, tz)


def compute_next_run(schedule) -> NextRun:
    """
    Compute next execution time for CRON schedules only.
    """
    if schedule.schedule_mode != ScheduleModeChoices.CRON:
        raise ValidationError(
            f"BUG: compute_next_run() called for non-cron schedule "
            f"(id={schedule.pk}, mode={schedule.schedule_mode})"
        )

    if not schedule.frequency:
        raise ValidationError({"frequency": "Frequency is required for cron scheduling."})

    now = timezone.localtime(timezone.now())
    tod = schedule.time_of_day

    def at(d: date) -> datetime:
        return _aware(datetime.combine(d, tod))

    # ---- DAILY ----
    if schedule.frequency == ScheduleFrequencyChoices.DAILY:
        c = at(now.date())
        return NextRun(c if c > now else at(now.date() + timedelta(days=1)))

    # ---- WEEKLY ----
    if schedule.frequency == ScheduleFrequencyChoices.WEEKLY:
        if schedule.weekday is None:
            raise ValidationError({"weekday": "Weekday required for weekly schedules."})

        target = int(schedule.weekday)
        delta = (target - now.weekday()) % 7
        cdate = now.date() + timedelta(days=delta)
        c = at(cdate)
        return NextRun(c if c > now else at(cdate + timedelta(days=7)))

    # ---- MONTHLY ----
    if schedule.frequency == ScheduleFrequencyChoices.MONTHLY:
        if schedule.day_of_month is None:
            raise ValidationError({"day_of_month": "Day of month required for monthly schedules."})

        dom = int(schedule.day_of_month)

        def last_dom(y: int, m: int) -> int:
            nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
            return (nxt - timedelta(days=1)).day

        y, m = now.year, now.month
        d = min(dom, last_dom(y, m))
        c = at(date(y, m, d))
        if c > now:
            return NextRun(c)

        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        d2 = min(dom, last_dom(y2, m2))
        return NextRun(at(date(y2, m2, d2)))

    raise ValidationError({"frequency": f"Invalid cron frequency: {schedule.frequency!r}"})


# =========================
# RUNNERS
# =========================

class _JobDataMixin:
    """
    Prevent clobbering Job.data by always merging with the latest DB value.
    """
    def update_job_data(self, **updates):
        # Refresh to avoid overwriting keys set by the view or earlier runner steps
        self.job.refresh_from_db(fields=["data"])
        data = self.job.data or {}
        data.update({k: v for k, v in updates.items() if v is not None})
        self.job.data = data
        self.job.save(update_fields=["data"])

    def seed_job_data(self, data=None) -> None:
        self.job.refresh_from_db(fields=["data"])
        job_data = self.job.data or {}
        changed = False

        if data:
            merged = {**job_data, **data}
            if merged != job_data:
                job_data = merged
                changed = True

        if changed:
            self.job.data = job_data
            self.job.save(update_fields=["data"])


class FortiGateInventoryPullRunner(_JobDataMixin, JobRunner):
    class Meta:
        name = "Inventory Pull"

    def run(self, schedule_id=None, device_id=None, data=None, *args, **kwargs):
        # ensure metadata exists before we write started_at/finished_at
        self.seed_job_data(data=data)

        # ✅ never write self.job.data directly
        self.update_job_data(started_at=timezone.now().isoformat())

        if device_id:
            device = FortiGateDevice.objects.get(pk=device_id)

            # TODO: do inventory for only this device

            self.update_job_data(
                finished_at=timezone.now().isoformat(),
                result="success",
            )
            return

        schedule = FortiGateScheduler.objects.get(pk=schedule_id)
        if not schedule.enabled:
            return

        # Initialize summary without overwriting trigger/meta
        self.job.refresh_from_db(fields=["data"])
        data = self.job.data or {}
        data.setdefault(
            "summary",
            {
                "devices_total": 0,
                "devices_ok": 0,
                "devices_failed": 0,
                "objects_created": 0,
                "objects_updated": 0,
            },
        )
        self.job.data = data
        self.job.save(update_fields=["data"])

        # TODO: do inventory work for schedule

        self.update_job_data(
            finished_at=timezone.now().isoformat(),
            result="success",
        )

        # ---- RESCHEDULE IF CRON ----
        if schedule.schedule_mode == ScheduleModeChoices.CRON:
            next_dt = compute_next_run(schedule).dt
            self.__class__.enqueue_once(
                instance=schedule,
                name=self.name,
                schedule_at=next_dt,
                interval=None,
                schedule_id=schedule.pk,
                trigger="cron",  # ✅ carry trigger forward
                meta={"schedule_id": schedule.pk, "schedule_name": schedule.name},
            )


class FortiGateRequestRunner(_JobDataMixin, JobRunner):
    class Meta:
        name = "Implement Request"

    def run(self, schedule_id, data=None, *args, **kwargs):
        self.seed_job_data(data=data)

        schedule = FortiGateScheduler.objects.get(pk=schedule_id)
        if not schedule.enabled:
            return

        # start
        self.update_job_data(started_at=timezone.now().isoformat())

        # ensure summary exists (merge-safe)
        self.job.refresh_from_db(fields=["data"])
        data = self.job.data or {}
        data.setdefault(
            "summary",
            {
                "devices_total": 0,
                "devices_ok": 0,
                "devices_failed": 0,
                "objects_created": 0,
                "objects_updated": 0,
            },
        )
        self.job.data = data
        self.job.save(update_fields=["data"])

        # TODO: do work...

        # finish
        self.update_job_data(
            finished_at=timezone.now().isoformat(),
            result="success",
        )

        # cron reschedule should tag the next job too
        if schedule.schedule_mode == ScheduleModeChoices.CRON:
            next_dt = compute_next_run(schedule).dt
            self.__class__.enqueue_once(
                instance=schedule,
                name=self.name,
                schedule_at=next_dt,
                interval=None,
                schedule_id=schedule.pk,
                trigger="cron",
                meta={"schedule_id": schedule.pk, "schedule_name": schedule.name},
            )
