from netbox.forms import NetBoxModelFilterSetForm
from django.contrib.contenttypes.models import ContentType

from ..models import *


__all__ = (
    "FortigateFilterForm",
    "InterfacesFilterForm",
    "ZoneFilterForm",
    "RoutingTableFilterForm",
    "ObjectFilterForm"
)


class FortigateFilterForm(NetBoxModelFilterSetForm):
    model = Fortigate

class InterfacesFilterForm(NetBoxModelFilterSetForm):
    model = Interfaces


class ZoneFilterForm(NetBoxModelFilterSetForm):
    model = Zone


class RoutingTableFilterForm(NetBoxModelFilterSetForm):
    model = RoutingTable


class ObjectFilterForm(NetBoxModelFilterSetForm):
    model = Object

    object_type_id = ContentType.objects.filter(app_label="netbox_fortigate")
