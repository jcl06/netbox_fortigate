import django_tables2 as tables

from netbox.tables import NetBoxTable

from ..models import *

__all__ = (
    "ObjectTable",
)


class ObjectTable(NetBoxTable):
    fortigate = tables.Column(linkify=True)
    object_type = tables.Column()
    object_id = tables.Column()

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