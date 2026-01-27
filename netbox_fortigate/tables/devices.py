import django_tables2 as tables

from netbox.tables import NetBoxTable

from ..models import *

__all__ = (
    "FortiGateDeviceTable",
    "FortiGateInterfaceTable",
    "FortiGateZoneTable",
    "FortiGateRouteTable",
    # "FortiGateObjectTable"
)

class FortiGateDeviceTable(NetBoxTable):
    device = tables.Column(linkify=True)
    role = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = FortiGateDevice
        fields = (
            "pk",
            "device",
            "ip_address",
            "role",
            "priority",
            "fortios_version",
            "default_vdom",
            "api_port",
            "ssh_port",
            "enabled",
            "last_updated",
        )



class FortiGateInterfaceTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = FortiGateInterface
        fields = (
            "pk",
            "name",
            "fortigate__device",
            "enabled",
            "ip",
            "type",
            "role",
            "parent",
            "vdom",
            "status",
            "last_updated",
        )


class FortiGateZoneTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    interface = tables.ManyToManyColumn()

    class Meta(NetBoxTable.Meta):
        model = FortiGateZone
        fields = (
            "pk",
            "name",
            "fortigate__device",
            "type",
            "intrazone",
            "interface",
            "last_updated",
        )



class FortiGateRouteTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    route = tables.Column(linkify=True)
    interface = tables.Column(linkify=True)
    next_hop = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = FortiGateRoute
        fields = (
            "pk",
            "route",
            "fortigate__device",
            "distance",
            "metric",
            "type",
            "gateway",
            "interface",
            "next_hop",
            "last_updated",
        )


