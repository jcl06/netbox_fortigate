from netbox.forms import NetBoxModelFilterSetForm
from django.contrib.contenttypes.models import ContentType

from ..models import *


__all__ = (
    "FortiGateDeviceFilterForm",
    "FortiGateInterfaceFilterForm",
    "FortiGateZoneFilterForm",
    "FortiGateRouteFilterForm",
    "FortiGateObjectFilterForm"
)


class FortiGateDeviceFilterForm(NetBoxModelFilterSetForm):
    model = FortiGateDevice

class FortiGateInterfaceFilterForm(NetBoxModelFilterSetForm):
    model = FortiGateInterface


class FortiGateZoneFilterForm(NetBoxModelFilterSetForm):
    model = FortiGateZone


class FortiGateRouteFilterForm(NetBoxModelFilterSetForm):
    model = FortiGateRoute


class FortiGateObjectFilterForm(NetBoxModelFilterSetForm):
    model = FortiGateObject

    object_type_id = ContentType.objects.filter(app_label="netbox_fortigate")
