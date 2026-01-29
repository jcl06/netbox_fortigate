from django.utils.translation import gettext_lazy as _
from utilities.choices import ChoiceSet
from django.db.models import Q

OBJECT_TYPE_CHOICES = (
    ("user", "User"),
    ("authentication server", "Authentication Server"),
    ("address", "Address"),
    ("address group", "Address Group"),
    ("service", "Service"),
    ("service group", "Service Group"),
    ("interface", "Interface"),
    ("zone", "Zone"),
    ("Virtual IP", "Virtual IP"),
    ("Virtual IP Group", "Virtual IP Group"),
    ("schedule onetime", "Schedule Onetime"),
    ("schedule recurring", "Schedule Recurring"),
    ("schedule group", "Schedule Group"),
)


CONTENT_TYPE_CHOICES = (
    Q(app_label="netbox_fortigate", model="fortigateinterface") |
    Q(app_label="netbox_fortigate", model="fortigatezone")
)



class JobTypeChoices(ChoiceSet):
    INVENTORY_PULL = "inventory_pull"
    IMPLEMENT_REQUEST = "implement_request"

    CHOICES = (
        (INVENTORY_PULL, _("Inventory pull")),
        (IMPLEMENT_REQUEST, _("Execute Request")),
    )

class ScheduleModeChoices(ChoiceSet):
    CRON = "cron"
    INTERVAL = "interval"

    CHOICES = (
        (CRON, _("Specific time (daily/weekly/monthly)")),
        (INTERVAL, _("Every N minutes")),
    )


class ScheduleFrequencyChoices(ChoiceSet):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    CHOICES = (
        (DAILY, _("Daily")),
        (WEEKLY, _("Weekly")),
        (MONTHLY, _("Monthly"))
    )


class WeekdayChoices(ChoiceSet):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    CHOICES = (
        (MONDAY, _("Monday")),
        (TUESDAY, _("Tuesday")),
        (WEDNESDAY, _("Wednesday")),
        (THURSDAY, _("Thursday")),
        (FRIDAY, _("Friday")),
        (SATURDAY, _("Saturday")),
        (SUNDAY, _("Sunday"))
    )
