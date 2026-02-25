import netaddr
import django_filters
from netaddr.core import AddrFormatError
from netbox.filtersets import NetBoxModelFilterSet
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from utilities.filters import MultiValueCharFilter

from .models import *

__all__ = (
    "FortigateFilterSet",
    "InterfacesFilterSet",
    "ZoneFilterSet",
    "RoutingTableFilterSet",
    "ObjectFilterSet",
    "SchedulerFilterSet"
)

class FortigateFilterSet(NetBoxModelFilterSet):
    device_id = django_filters.NumberFilter(field_name="device_id")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    role = django_filters.CharFilter(field_name="role", lookup_expr="icontains")

    class Meta:
        model = Fortigate
        fields = ("device_id", "enabled", "role", "priority", "default_vdom")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(device__name__icontains=value) |
            Q(mgmt_ip__address__startwith=value) 
        )



class InterfacesFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    role = django_filters.CharFilter(field_name="role")
    vdom = django_filters.CharFilter(field_name="vdom", lookup_expr="icontains")
    status = django_filters.CharFilter(field_name="status")

    class Meta:
        model = Interfaces
        fields = ("fortigate_id", "name", "enabled", "role", "vdom", "status")


class ZoneFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    type = django_filters.CharFilter(field_name="type")
    intrazone = django_filters.CharFilter(field_name="intrazone")

    class Meta:
        model = Zone
        fields = ("fortigate_id", "name", "type", "intrazone")


class RoutingTableFilterSet(NetBoxModelFilterSet):
    prefix = MultiValueCharFilter(
        method="filter_prefix",
        label="Prefix",
    )
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    version = django_filters.NumberFilter(field_name="version")
    type = django_filters.CharFilter(field_name="type", lookup_expr="icontains")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    interface_id = django_filters.NumberFilter(field_name="interface_id")

    class Meta:
        model = RoutingTable
        fields = ("fortigate_id", "version", "type", "enabled", "interface_id")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = Q(description__icontains=value)
        qs_filter |= Q(route__contains=value.strip())
        qs_filter |= Q(type__icontains=value)
        qs_filter |= Q(gateway__contains=value)
        try:
            prefix = str(netaddr.IPNetwork(value.strip()).cidr)
            qs_filter |= Q(route__net_contains_or_equals=prefix)
            qs_filter |= Q(route__contains=value.strip())
        except (AddrFormatError, ValueError):
            pass
        return queryset.filter(qs_filter)

    def filter_prefix(self, queryset, name, value):
        query_values = []
        for v in value:
            try:
                query_values.append(netaddr.IPNetwork(v))
            except (AddrFormatError, ValueError):
                pass
        return queryset.filter(route__in=query_values)


class ObjectFilterSet(NetBoxModelFilterSet):
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
        model = Object
        fields = (
            "fortigate_id",
            "enabled",
            "type",
            "name",
            "object_type_id",
            "object_id",
        )






class SchedulerFilterSet(NetBoxModelFilterSet):
    enabled = django_filters.BooleanFilter()
    job_type = django_filters.CharFilter()
    schedule_mode = django_filters.CharFilter()
    frequency = django_filters.CharFilter()

    class Meta:
        model = Scheduler
        fields = (
            "name",
            "enabled",
            "job_type",
            "schedule_mode",
            "frequency"
        )