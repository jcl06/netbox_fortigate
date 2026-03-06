import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from ..models import *

__all__ = (
    "ObjectTable",
    'AddressTable',
    'AddressGroupTable',
    'ServicesTable',
    'ServiceGroupTable',
    'VIPTable',
    'VIPGroupTable',
    'ScheduleOnetimeTable',
    'ScheduleRecurringTable',
    'ScheduleGroupTable',
    'UserTable',
    'AuthenticationServerTable'
)


class ObjectTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    object_type = tables.Column()
    object_id = tables.Column()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = Object
        fields = (
            "pk",
            "name",
            "fortigate",
            "enabled",
            "type",
            "object_type",
            "object_id",
            "last_updated",
        )



class AddressTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    type = columns.ChoiceFieldColumn()
    subnet = tables.Column()
    start_ip = tables.Column()
    end_ip = tables.Column()
    fqdn = tables.Column()
    is_decommissioned = tables.BooleanColumn()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = Address
        fields = (
            "pk", "id", "name", "fortigate", "type",
            "subnet", "start_ip", "end_ip", "fqdn",
            "is_decommissioned", "actions",
        )
        default_columns = ("name", "fortigate", "type", "subnet", "fqdn")


class AddressGroupTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    type = columns.ChoiceFieldColumn()
    member_count = tables.Column(empty_values=(), orderable=False, verbose_name="Members")
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = AddressGroup
        fields = ("pk", "id", "name", "fortigate", "type", "member_count", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "type", "member_count")

    def render_member_count(self, record):
        return record.member.count()


class ServicesTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    protocol = columns.ChoiceFieldColumn()
    protocol_number = tables.Column()
    icmptype = tables.Column()
    tcp_portrange = tables.Column()
    udp_portrange = tables.Column()
    is_decommissioned = tables.BooleanColumn()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = Services
        fields = (
            "pk", "id", "name", "fortigate", "protocol",
            "protocol_number", "icmptype", "tcp_portrange", "udp_portrange",
            "is_decommissioned", "actions",
        )
        default_columns = ("name", "fortigate", "protocol", "tcp_portrange", "udp_portrange")


class ServiceGroupTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    member_count = tables.Column(empty_values=(), orderable=False, verbose_name="Members")
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = ServiceGroup
        fields = ("pk", "id", "name", "fortigate", "member_count", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "member_count")

    def render_member_count(self, record):
        return record.member.count()


class VIPTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    type = columns.ChoiceFieldColumn()
    external_ip = tables.Column()
    mapped_ip = tables.Column()
    external_interface = tables.Column()
    status = columns.ChoiceFieldColumn()
    is_decommissioned = tables.BooleanColumn()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = VIP
        fields = (
            "pk", "id", "name", "fortigate", "type",
            "external_ip", "mapped_ip", "external_interface", "status",
            "is_decommissioned", "actions",
        )
        default_columns = ("name", "fortigate", "type", "external_ip", "mapped_ip", "status")


class VIPGroupTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    interface = tables.Column()
    member_count = tables.Column(empty_values=(), orderable=False, verbose_name="Members")
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = VIPGroup
        fields = ("pk", "id", "name", "fortigate", "interface", "member_count", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "interface", "member_count")

    def render_member_count(self, record):
        return record.member.count()


class ScheduleOnetimeTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    start = tables.DateTimeColumn()
    end = tables.DateTimeColumn()
    is_decommissioned = tables.BooleanColumn()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = ScheduleOnetime
        fields = ("pk", "id", "name", "fortigate", "start", "end", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "start", "end")


class ScheduleRecurringTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    start = tables.TimeColumn()
    end = tables.TimeColumn()
    day = tables.Column()
    is_decommissioned = tables.BooleanColumn()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = ScheduleRecurring
        fields = ("pk", "id", "name", "fortigate", "start", "end", "day", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "start", "end", "day")


class ScheduleGroupTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    member_count = tables.Column(empty_values=(), orderable=False, verbose_name="Members")
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = ScheduleGroup
        fields = ("pk", "id", "name", "fortigate", "member_count", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "member_count")

    def render_member_count(self, record):
        return record.member.count()


class UserTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    type = columns.ChoiceFieldColumn()
    status = columns.ChoiceFieldColumn()
    server = tables.Column(linkify=True)
    is_decommissioned = tables.BooleanColumn()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = User
        fields = ("pk", "id", "name", "fortigate", "type", "status", "server", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "type", "status", "server")


class AuthenticationServerTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    type = columns.ChoiceFieldColumn()
    server = tables.Column()
    is_decommissioned = tables.BooleanColumn()
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = AuthenticationServer
        fields = ("pk", "id", "name", "fortigate", "type", "server", "is_decommissioned", "actions")
        default_columns = ("name", "fortigate", "type", "server")

