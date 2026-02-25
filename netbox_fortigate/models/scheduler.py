from __future__ import annotations

from datetime import time
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from netbox.models import PrimaryModel, JobsMixin

from ..choices import *

__all__ =(
    "Scheduler",
)


class Scheduler(PrimaryModel, JobsMixin):
    """
    A cron-like schedule for plugin automation.

    - Daily at HH:MM
    - Weekly on weekday at HH:MM
    - Monthly on day-of-month at HH:MM
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("A unique name for this schedule (shown in the UI and job names)."),
    )

    enabled = models.BooleanField(
        default=True,
        verbose_name=_("Enabled"),
        help_text=_("If disabled, future queued runs for this schedule will be removed and no new runs will be scheduled."),
    )

    job_type = models.CharField(
        max_length=64,
        choices=JobTypeChoices,
        verbose_name=_("Job Type"),
        help_text=_("Which automation this schedule will run (e.g., inventory pull or approved-request executor)."),
    )

    schedule_mode = models.CharField(
        max_length=32,
        choices=ScheduleModeChoices,
        default=ScheduleModeChoices.CRON,
        verbose_name=_("Mode"),
        help_text=_("Choose a specific time (daily/weekly/monthly) or run repeatedly every N minutes."),
    )

    interval_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Interval"),
        help_text=_("Used only for 'Every N minutes'. Example: 15 means run every 15 minutes."),
    )

    frequency = models.CharField(
        max_length=16,
        choices=ScheduleFrequencyChoices,
        null=True,
        blank=True,
        verbose_name=_("Frequency"),
        help_text=_("Used only for 'Specific time'. Choose daily, weekly, or monthly."),
    )

    time_of_day = models.TimeField(
        blank=True,
        null=True,
        verbose_name=_("Time of day"),
        help_text=_("Used only for 'Specific time'. The local NetBox time when the job should run (e.g. 01:00)."),
    )

    weekday = models.PositiveSmallIntegerField(
        choices=WeekdayChoices,
        null=True,
        blank=True,
        verbose_name=_("Weekday"),
        help_text=_("Required for weekly schedules. Ignored for daily/monthly schedules and interval mode."),
    )

    day_of_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Day of month"),
        help_text=_("Required for monthly schedules (1-31). If a month is shorter, the job will run on the month's last day."),
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    # Optional: if you want schedules in a specific TZ rather than server TZ, add a tz field
    # timezone = models.CharField(max_length=64, default="UTC")

    def get_absolute_url(self):
        return reverse('plugins:netbox_fortigate:scheduler', args=[self.pk])


    class Meta:
        ordering = ("name",)
        verbose_name = "Job Scheduler"
        verbose_name_plural = "Job Schedulers"
        constraints = [
            # Interval schedules: unique per (job_type, interval_minutes)
            models.UniqueConstraint(
                fields=["job_type", "interval_minutes"],
                condition=Q(schedule_mode="interval"),
                name="uniq_fgt_sched_interval_jobtype_minutes",
            ),
            # Cron schedules: unique per (job_type, frequency, time_of_day, weekday, day_of_month)
            models.UniqueConstraint(
                fields=["job_type", "frequency", "time_of_day", "weekday", "day_of_month"],
                condition=Q(schedule_mode="cron"),
                name="uniq_fgt_sched_cron_jobtype_when",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()

        if self.schedule_mode == ScheduleModeChoices.INTERVAL:
            if not self.interval_minutes or self.interval_minutes < 1:
                raise ValidationError({"interval_minutes": "Required for interval scheduling (>= 1)."})
            self.frequency = None
            self.weekday = None
            self.day_of_month = None

        if self.schedule_mode == ScheduleModeChoices.CRON:
            if not self.frequency:
                raise ValidationError({"frequency": "Required for cron scheduling."})

            if self.frequency == ScheduleFrequencyChoices.WEEKLY and self.weekday is None:
                raise ValidationError({"weekday": "Required for weekly schedules."})

            if self.frequency == ScheduleFrequencyChoices.MONTHLY:
                if self.day_of_month is None:
                    raise ValidationError({"day_of_month": "Required for monthly schedules."})
                if not (1 <= self.day_of_month <= 31):
                    raise ValidationError({"day_of_month": "Must be between 1 and 31."})

            self.interval_minutes = None
