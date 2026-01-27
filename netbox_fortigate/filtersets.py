import django_filters

from netbox.filtersets import NetBoxModelFilterSet
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import *

__all__ = (
    "FortiGateDeviceFilterSet",
    "FortiGateInterfaceFilterSet",
    "FortiGateZoneFilterSet",
    "FortiGateRouteFilterSet",
    "FortiGateObjectFilterSet"
)

class FortiGateDeviceFilterSet(NetBoxModelFilterSet):
    device_id = django_filters.NumberFilter(field_name="device_id")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    role = django_filters.CharFilter(field_name="role", lookup_expr="icontains")

    class Meta:
        model = FortiGateDevice
        fields = ("device_id", "enabled", "role", "priority", "default_vdom")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(device__name__icontains=value) |
            Q(mgmt_ip__address__startwith=value) 
        )



class FortiGateInterfaceFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    role = django_filters.CharFilter(field_name="role")
    vdom = django_filters.CharFilter(field_name="vdom", lookup_expr="icontains")
    status = django_filters.CharFilter(field_name="status")

    class Meta:
        model = FortiGateInterface
        fields = ("fortigate_id", "name", "enabled", "role", "vdom", "status")


class FortiGateZoneFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    type = django_filters.CharFilter(field_name="type")
    intrazone = django_filters.CharFilter(field_name="intrazone")

    class Meta:
        model = FortiGateZone
        fields = ("fortigate_id", "name", "type", "intrazone")


class FortiGateRouteFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    version = django_filters.NumberFilter(field_name="version")
    type = django_filters.CharFilter(field_name="type", lookup_expr="icontains")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    interface_id = django_filters.NumberFilter(field_name="interface_id")

    class Meta:
        model = FortiGateRoute
        fields = ("fortigate_id", "version", "type", "enabled", "interface_id")


class FortiGateObjectFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    enabled = django_filters.BooleanFilter(field_name="enabled")

    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    type = django_filters.CharFilter(field_name="type", lookup_expr="exact")

    object_type_id = django_filters.ModelChoiceFilter(
        field_name="object_type",
        queryset=ContentType.objects.filter(app_label="netbox_fortigate"),
        label="Object type",
    )
    object_id = django_filters.NumberFilter(field_name="object_id")

    class Meta:
        model = FortiGateObject
        fields = (
            "fortigate_id",
            "enabled",
            "type",
            "name",
            "object_type_id",
            "object_id",
        )



