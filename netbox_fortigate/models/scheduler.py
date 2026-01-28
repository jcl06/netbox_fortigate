from __future__ import annotations

from datetime import time
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from ..choices import *

__all__ =(
    "FortiGateScheduler",
)


class FortiGateScheduler(NetBoxModel):
    """
    A cron-like schedule for plugin automation.

    - Daily at HH:MM
    - Weekly on weekday at HH:MM
    - Monthly on day-of-month at HH:MM
    """
    name = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=True)

    frequency = models.CharField(
        max_length=10,
        choices=ScheduleFrequencyChoices,
        default=ScheduleFrequencyChoices.DAILY,
    )

    time_of_day = models.TimeField(default=time(1, 0))  # 01:00 by default

    # Weekly
    weekday = models.IntegerField(
        choices=WeekdayChoices,
        null=True,
        blank=True,
        help_text="Required when frequency is weekly",
    )

    # Monthly
    day_of_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="1-31 (required when frequency is monthly)",
    )

    # Optional: if you want schedules in a specific TZ rather than server TZ, add a tz field
    # timezone = models.CharField(max_length=64, default="UTC")

    # def get_absolute_url(self):
    #     return reverse('netbox_fortigate:fortigatescheduler', args=[self.pk])


    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()

        if self.frequency == ScheduleFrequencyChoices.WEEKLY:
            if self.weekday is None:
                raise ValidationError({"weekday": "weekday is required for weekly schedules"})
            self.day_of_month = None

        if self.frequency == ScheduleFrequencyChoices.MONTHLY:
            if self.day_of_month is None:
                raise ValidationError({"day_of_month": "day_of_month is required for monthly schedules"})
            if not (1 <= self.day_of_month <= 31):
                raise ValidationError({"day_of_month": "Must be between 1 and 31"})
            self.weekday = None

        if self.frequency == ScheduleFrequencyChoices.DAILY:
            self.weekday = None
            self.day_of_month = None
