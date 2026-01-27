# netbox_fortigate/choices.py
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
