from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from netbox.jobs import JobRunner
from dcim.models import Device

from .models import FortiGateScheduler
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


def compute_next_run(schedule: FortiGateScheduler) -> NextRun:
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

class FortiGateInventoryPullRunner(JobRunner):
    class Meta:
        name = "Firewall: Inventory Pull"

    def run(self, schedule_id: int | None = None, device_id: int | None = None, *args, **kwargs) -> None:
        if device_id:
            device = Device.objects.get(pk=device_id)
            # do inventory for only this device
            self.job.data = {
                **(self.job.data or {}),
                "started_at": timezone.now().isoformat(),
            }
            self.job.save()

            # --- do work, update counters along the way ---
            # summary = self.job.data["summary"]
            # summary["devices_total"] += 1
            # summary["devices_ok"] += 1
            # summary["objects_updated"] += 5
            # self.job.save(update_fields=["data"])

            # Finish summary
            self.job.data = {
                **(self.job.data or {}),
                "finished_at": timezone.now().isoformat(),
                "result": "success",
            }
            self.job.save(update_fields=["data"])
            return
        
        schedule = FortiGateScheduler.objects.get(pk=schedule_id)

        if not schedule.enabled:
            return

        # ---- DO INVENTORY WORK HERE ----
        # - connect to FortiGate
        # - pull inventory
        # - update NetBox objects
        self.job.data = {
            **(self.job.data or {}),
            "started_at": timezone.now().isoformat(),
            "summary": {
                "devices_total": 0,
                "devices_ok": 0,
                "devices_failed": 0,
                "objects_created": 0,
                "objects_updated": 0,
            },
        }
        self.job.save()

        # --- do work, update counters along the way ---
        # summary = self.job.data["summary"]
        # summary["devices_total"] += 1
        # summary["devices_ok"] += 1
        # summary["objects_updated"] += 5
        # self.job.save(update_fields=["data"])

        # Finish summary
        self.job.data = {
            **(self.job.data or {}),
            "finished_at": timezone.now().isoformat(),
            "result": "success",
        }
        self.job.save(update_fields=["data"])

        # ---- RESCHEDULE IF CRON ----
        if schedule.schedule_mode == ScheduleModeChoices.CRON:
            next_dt = compute_next_run(schedule).dt
            self.__class__.enqueue_once(
                instance=schedule,
                name=self.name,
                schedule_at=next_dt,
                interval=None,
                schedule_id=schedule.pk,
            )
        # interval mode → NetBox auto-reschedules


class FortiGateRequestRunner(JobRunner):
    class Meta:
        name = "Firewall: Implement Request"

    def run(self, schedule_id: int, *args, **kwargs) -> None:
        schedule = FortiGateScheduler.objects.get(pk=schedule_id)

        if not schedule.enabled:
            return

        # ---- DO REQUEST EXECUTION HERE ----
        # - find approved requests
        # - push firewall changes
        # - update request status
        # Start summary
        self.job.data = {
            **(self.job.data or {}),
            "started_at": timezone.now().isoformat(),
            "summary": {
                "devices_total": 0,
                "devices_ok": 0,
                "devices_failed": 0,
                "objects_created": 0,
                "objects_updated": 0,
            },
        }
        self.job.save()

        # --- do work, update counters along the way ---
        # summary = self.job.data["summary"]
        # summary["devices_total"] += 1
        # summary["devices_ok"] += 1
        # summary["objects_updated"] += 5
        # self.job.save(update_fields=["data"])

        # Finish summary
        self.job.data = {
            **(self.job.data or {}),
            "finished_at": timezone.now().isoformat(),
            "result": "success",
        }
        self.job.save(update_fields=["data"])

        # ---- RESCHEDULE IF CRON ----
        if schedule.schedule_mode == ScheduleModeChoices.CRON:
            next_dt = compute_next_run(schedule).dt
            self.__class__.enqueue_once(
                instance=schedule,
                name=self.name,
                schedule_at=next_dt,
                interval=None,
                schedule_id=schedule.pk,
            )
        # interval mode → NetBox auto-reschedules
