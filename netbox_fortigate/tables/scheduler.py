import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from ..models import Scheduler

__all__ = (
    "SchedulerTable",
)


class SchedulerTable(NetBoxTable):
    name = tables.Column(linkify=True)
    enabled = columns.BooleanColumn()

    job_type = tables.Column(verbose_name="Job type")
    schedule_mode = tables.Column(verbose_name="Schedule mode")

    # Interval mode
    interval_minutes = tables.Column(verbose_name="Interval (min)")

    # Cron mode
    frequency = tables.Column(verbose_name="Frequency")
    time_of_day = tables.Column(verbose_name="Time")
    weekday = tables.Column(verbose_name="Weekday")
    day_of_month = tables.Column(verbose_name="Day of month")

    class Meta(NetBoxTable.Meta):
        model = Scheduler
        fields = (
            "pk",
            "id",
            "name",
            "enabled",
            "job_type",
            "schedule_mode",
            "interval_minutes",
            "frequency",
            "time_of_day",
            "weekday",
            "day_of_month",
        )
        default_columns = (
            "name",
            "enabled",
            "job_type",
            "schedule_mode",
            "interval_minutes",
            "frequency",
            "time_of_day",
            "weekday",
            "day_of_month",
        )
