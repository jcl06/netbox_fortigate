import django_tables2 as tables

from netbox.tables import NetBoxTable, columns


from ..models import *

__all__ = (
    "FortigateTable",
    "InterfacesTable",
    "ZoneTable",
    "RoutingTableTable",
)

class FortigateTable(NetBoxTable):
    id = tables.Column(linkify=True)
    device = tables.Column(linkify=True)
    role = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = Fortigate
        fields = (
            "pk",
            "id",
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



class InterfacesTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = Interfaces
        fields = (
            "pk",
            "name",
            "fortigate",
            "enabled",
            "ip",
            "type",
            "role",
            "parent",
            "vdom",
            "status",
            "last_updated",
        )


class ZoneTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = Zone
        fields = (
            "pk",
            "name",
            "fortigate",
            "type",
            "intrazone",
            "last_updated",
        )



class RoutingTableTable(NetBoxTable):
    route = tables.Column(linkify=True)
    fortigate = tables.Column(linkify=True)
    interface = tables.Column(linkify=True)
    next_hop = tables.Column(linkify=True)
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )
    class Meta(NetBoxTable.Meta):
        model = RoutingTable
        fields = (
            "pk",
            "route",
            "fortigate",
            "distance",
            "metric",
            "type",
            "gateway",
            "interface",
            "next_hop",
            "last_updated",
        )


