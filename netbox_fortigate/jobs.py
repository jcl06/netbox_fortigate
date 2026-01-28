from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from django.utils import timezone

from netbox.jobs import JobRunner
from .models import FortiGateScheduler
from .choices import ScheduleFrequencyChoices


@dataclass(frozen=True)
class NextRun:
    dt: datetime


def _make_aware_local(dt: datetime) -> datetime:
    """
    Make dt timezone-aware in the current Django timezone.
    """
    tz = timezone.get_current_timezone()
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, tz)


def compute_next_run(schedule: FortiGateScheduler) -> NextRun:
    """
    Compute next run datetime in the current Django timezone.

    Monthly rule:
    - If day_of_month doesn't exist in a month (e.g., 31 in February), we schedule on the *last day* of that month.
    """
    now = timezone.localtime(timezone.now())
    tod = schedule.time_of_day

    def at(d: date) -> datetime:
        return _make_aware_local(datetime.combine(d, tod))

    if schedule.frequency == ScheduleFrequencyChoices.DAILY:
        candidate = at(now.date())
        if candidate > now:
            return NextRun(candidate)
        return NextRun(at(now.date() + timedelta(days=1)))

    if schedule.frequency == ScheduleFrequencyChoices.WEEKLY:
        # weekday: Monday=0 ... Sunday=6
        target = int(schedule.weekday)
        today = now.date()
        delta = (target - today.weekday()) % 7
        candidate_date = today + timedelta(days=delta)
        candidate = at(candidate_date)
        if candidate > now:
            return NextRun(candidate)
        # same weekday next week
        return NextRun(at(today + timedelta(days=delta + 7)))

    if schedule.frequency == ScheduleFrequencyChoices.MONTHLY:
        dom = int(schedule.day_of_month)

        def last_day_of_month(y: int, m: int) -> int:
            if m == 12:
                nxt = date(y + 1, 1, 1)
            else:
                nxt = date(y, m + 1, 1)
            return (nxt - timedelta(days=1)).day

        y, m = now.year, now.month
        ld = last_day_of_month(y, m)
        day = min(dom, ld)
        candidate = at(date(y, m, day))
        if candidate > now:
            return NextRun(candidate)

        # next month
        if m == 12:
            y2, m2 = y + 1, 1
        else:
            y2, m2 = y, m + 1
        ld2 = last_day_of_month(y2, m2)
        day2 = min(dom, ld2)
        return NextRun(at(date(y2, m2, day2)))

    raise ValueError(f"Unknown frequency: {schedule.frequency}")


class FortiGateRunner(JobRunner):
    """
    Runs one automation cycle and schedules the next run via schedule_at.
    """

    class Meta:
        name = "Fortinet Automation"

    def run(self, schedule_id: int, *args, **kwargs) -> None:
        schedule = FortiGateScheduler.objects.get(pk=schedule_id)

        if not schedule.enabled:
            return

        # TODO: put your pull/push logic here
        # Example shape:
        # - resolve devices
        # - connect
        # - push/pull
        # - update NetBox

        # After finishing, schedule the next run time
        next_dt = compute_next_run(schedule).dt

        # IMPORTANT: use schedule_at, NOT interval, so we get cron-like behavior.
        self.__class__.enqueue_once(
            instance=schedule,
            schedule_at=next_dt,
            interval=None,
            schedule_id=schedule.pk,
        )
