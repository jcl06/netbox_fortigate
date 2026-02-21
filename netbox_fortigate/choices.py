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
    Q(app_label='netbox_fortigate', model='fortigateinterface') |
    Q(app_label='netbox_fortigate', model='fortigatezone') |
    Q(app_label='netbox_fortigate', model='fortigateaddress') |
    Q(app_label='netbox_fortigate', model='fortigateaddressgroup') |
    Q(app_label='netbox_fortigate', model='fortigateservice') |
    Q(app_label='netbox_fortigate', model='fortigateservicegroup') |
    Q(app_label='netbox_fortigate', model='fortigatevip') |
    Q(app_label='netbox_fortigate', model='fortigatevipgroup') |
    Q(app_label='netbox_fortigate', model='fortigatescheduleonetime') |
    Q(app_label='netbox_fortigate', model='fortigateschedulerecurring') |
    Q(app_label='netbox_fortigate', model='fortigateschedulegroup') |
    Q(app_label='netbox_fortigate', model='fortigateuser') |
    Q(app_label='netbox_fortigate', model='fortigateauthenticationserver') 
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


SUPPORTED_DEVICE_TYPE = (
    ('FORTIGATE', 'FORTIGATE'),
)

DEVICE_ROLE = (
    ('firewall', 'Firewall'),
    ('user_vpn', 'User VPN'),
    ('edge', 'Edge')
)

SUPPORTED_POLICY_DEVICE_ROLE = [
    'firewall',
    'user_vpn'
]

ADDRESS_TYPE_CHOICES = (
    ('ipmask', 'IP/Network Address'),
    ('iprange', 'IP Range'),
    ('fqdn', 'FQDN'),
)

VIP_TYPE_CHOICES = (
    ('static-nat', 'Static NAT'),
    ('fqdn', 'FQDN'),
)

PORT_FORWARDING_PROTOCOL_CHOICES = (
    ('tcp', 'TCP'),
    ('udp', 'UDP'),
    ('icmp', 'ICMP'),
    ('sctp', 'SCTP'),
)

DAY_CHOICES = (
    ('monday', 'Monday'),
    ('tuesday', 'Tuesday'),
    ('wednesday', 'Wednesday'),
    ('thursday', 'Thursday'),
    ('friday', 'Friday'),
    ('saturday', 'Saturday'),
    ('sunday', 'Sunday'),
    ('none', 'None')
)


class ServiceProtocolChoices(ChoiceSet):

    DEFAULT = 'TCP/UDP/UDP-Lite/SCTP'
    ICMP = 'ICMP'
    ICMP6 = 'ICMP6'
    IP = 'IP'
    HTTP = 'HTTP'
    FTP = 'FTP'
    CONNECT = 'CONNECT'
    SOCKS_TCP = 'SOCKS-TCP'
    SOCKS_UDP = 'SOCKS-UDP'
    ALL = 'ALL'

    CHOICES = (
        (DEFAULT, DEFAULT),
        (ICMP, ICMP),
        (ICMP6, ICMP6),
        (IP, IP),
        (HTTP, HTTP),
        (FTP, FTP),
        (CONNECT, CONNECT),
        (SOCKS_TCP, SOCKS_TCP),
        (SOCKS_UDP, SOCKS_UDP),
        (ALL, ALL)
    )


class IPPoolTypeChoices(ChoiceSet):

    DEFAULT = 'overload'
    ONE_TO_ONE = 'one-to-one'
    FIXED_PORT_RANGE = 'fixed-port-range'
    PORT_BLOCK_ALLOCATION = 'port-block-allocation'

    CHOICES = (
        (DEFAULT, 'Overload'),
        (ONE_TO_ONE, 'One-to-One'),
        (FIXED_PORT_RANGE, 'Fixed Port Range'),
        (PORT_BLOCK_ALLOCATION, 'Port Block Allocation')

    )
