from __future__ import annotations
import uuid

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.exceptions import ValidationError
from django.db import close_old_connections 
from django.utils import timezone
from django.contrib.auth import get_user_model

from netbox.context import current_request, events_queue
from netbox.jobs import JobRunner
from .utils.settings import get_plugin_default
from .utils.inventory import update_inventory

from .models import Scheduler, Fortigate
from .choices import ScheduleFrequencyChoices, ScheduleModeChoices



User = get_user_model()

SYSTEM_USERNAME = get_plugin_default("SYSTEM_USERNAME", "system")

def _resolve_audit_user(job) -> User:
    """
    For manual runs, NetBox attaches job.user.
    For scheduled runs, job.user is often None -> fall back to an existing 'system' user.
    """
    user = getattr(job, "user", None)
    if user is not None:
        return user

    system_user = User.objects.filter(username=SYSTEM_USERNAME).first()
    if system_user is None:
        system_user = User.objects.create(username=SYSTEM_USERNAME, is_active=False)
    return system_user


@dataclass
class _JobRequest:
    id: object
    user: object

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


class InventoryPullRunner(_JobDataMixin, JobRunner):
    class Meta:
        name = "Inventory Pull"

    def run(self, schedule_id=None, fortigate_id=None, data=None, *args, **kwargs):
        user = _resolve_audit_user(self.job)
        req = _JobRequest(id=uuid.uuid4(), user=user)

        # ensure metadata exists before we write started_at/finished_at
        self.seed_job_data(data=data)

        self.update_job_data(started_at=timezone.now().isoformat())

        DEBUG = get_plugin_default("DEBUG", False)
        max_workers = get_plugin_default("inventory_max_workers", 10)

        if fortigate_id:
            devices = list(Fortigate.objects.filter(pk=fortigate_id))
        else:
            schedule = Scheduler.objects.get(pk=schedule_id)
            if not schedule.enabled:
                return
            
            devices = list(Fortigate.objects.filter(enabled=True))

        items: list[dict] = []
        failed = success = with_errors = 0

        def worker(id: int):
            close_old_connections()
            fg = Fortigate.objects.get(pk=id)
            if get_plugin_default("enable_logging", False):
                current_request.set(req)
            # IMPORTANT: do not rewrite update_inventory here; just call it
            # Expected return: [ok(bool), state_or_error(str), items(list)]
            result = update_inventory(fg, DEBUG=DEBUG, job=self)
            return id, result

        results_by_id = {}

        if max_workers <= 1 or len(devices) <= 1:
            for fg in devices:
                if get_plugin_default("enable_logging", False):
                    current_request.set(req)
                id, result = fg.pk, update_inventory(fg, DEBUG=DEBUG, job=self)
                results_by_id[id] = result
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(worker, fg.pk) for fg in devices]
                for fut in as_completed(futures):
                    id, result = fut.result()
                    results_by_id[id] = result

        # ---- process results (ported from process_inventory_results) ----
        for fg in devices:
            status = results_by_id.get(fg.pk, [False, "No result", []])

            ok = bool(status[0])
            if not ok:
                # status[1] is error message
                items.append(
                    {
                        "device": fg.device.name,
                        "job name": "inventory pull",
                        "status": "Failed",
                        "errors": status,
                    }
                )
                failed += 1
                # status[2] may contain partial per-category items
                if len(status) >= 3:
                    items += (status[2] or [])
                continue

            # status[1] is state string when ok=True
            if status[1] == "Successful":
                success += 1
            elif status[1] == "Successful with Errors":
                with_errors += 1
            else:
                # treat unknown state as with_errors but keep data
                failed += 1

            if len(status) >= 3:
                items += (status[2] or [])
            

        # Determine job result (ported from pull_inventories)
        if len(devices) == failed and failed > 0:
            state = "Failed"
        elif len(devices) == success and success > 0 and with_errors == 0:
            state = "Successful"
        else:
            state = "Successful with Errors"

        started = timezone.localtime().strftime("%b-%d-%Y %H:%M")

        # ---- write job data (merge-safe) ----
        self.job.refresh_from_db(fields=["data"])
        job_data = self.job.data or {}
        job_data.setdefault("summary", {})
        job_data["summary"].update(
            {
                "devices_total": len(devices),
                "successful": success,
                "failed": failed,
                "successful_with_errors": with_errors,
            }
        )
        job_data.update(
            {
                "items": items,            
                "time_started": started,
                "state": state,
            }
        )
        self.job.data = job_data
        self.job.save(update_fields=["data"])
        self.update_job_data(finished_at=timezone.now().isoformat())
                
        # ---- RESCHEDULE IF CRON ----
        if not fortigate_id:
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

        if state == "Failed":
            self.logger.error(f"Inventory pull failed for {failed} device(s)")
            raise RuntimeError(f"Inventory pull failed for {failed} device(s)")



class RequestRunner(_JobDataMixin, JobRunner):
    class Meta:
        name = "Implement Request"

    def run(self, schedule_id, data=None, *args, **kwargs):
        self.seed_job_data(data=data)

        schedule = Scheduler.objects.get(pk=schedule_id)
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
