import netaddr
import django_filters
from netaddr.core import AddrFormatError
from netbox.filtersets import NetBoxModelFilterSet
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from utilities.filters import MultiValueCharFilter
from django.utils.translation import gettext as _

from .models import *

__all__ = (
    "FortigateFilterSet",
    "InterfacesFilterSet",
    "ZoneFilterSet",
    "RoutingTableFilterSet",
    "ObjectFilterSet",
    "SchedulerFilterSet",
    "PolicyFilterSet"
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


class AddressFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    type = django_filters.CharFilter(field_name="type")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = Address
        fields = ("q", "fortigate_id", "type", "is_decommissioned")


class AddressGroupFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    type = django_filters.CharFilter(field_name="type")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = AddressGroup
        fields = ("q", "fortigate_id", "type", "is_decommissioned")


class ServicesFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    protocol = django_filters.CharFilter(field_name="protocol")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = Services
        fields = ("q", "fortigate_id", "protocol", "is_decommissioned")


class ServiceGroupFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = ServiceGroup
        fields = ("q", "fortigate_id", "is_decommissioned")


class VIPFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    type = django_filters.CharFilter(field_name="type")
    status = django_filters.CharFilter(field_name="status")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = VIP
        fields = ("q", "fortigate_id", "type", "status", "is_decommissioned")


class VIPGroupFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    interface = django_filters.CharFilter(field_name="interface")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = VIPGroup
        fields = ("q", "fortigate_id", "interface", "is_decommissioned")


class ScheduleOnetimeFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = ScheduleOnetime
        fields = ("q", "fortigate_id", "is_decommissioned")


class ScheduleRecurringFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    day = django_filters.CharFilter(field_name="day")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = ScheduleRecurring
        fields = ("q", "fortigate_id", "day", "is_decommissioned")


class ScheduleGroupFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = ScheduleGroup
        fields = ("q", "fortigate_id", "is_decommissioned")


class UserFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    type = django_filters.CharFilter(field_name="type")
    status = django_filters.CharFilter(field_name="status")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = User
        fields = ("q", "fortigate_id", "type", "status", "is_decommissioned")


class AuthenticationServerFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    type = django_filters.CharFilter(field_name="type")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = AuthenticationServer
        fields = ("q", "fortigate_id", "type", "is_decommissioned")



class PolicyFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Fortigate.objects.all(),
        label=_('Fortigate (ID)'),
    )
    policy_id = django_filters.ModelMultipleChoiceFilter(
        field_name='policyid',
        to_field_name='policyid',
        queryset=Policy.objects.all(),
        label="Policy ID",
    )
    source_interface_id = django_filters.ModelMultipleChoiceFilter(
        label=_("Source Interface"),
        queryset=Interfaces.objects.all(),
        method="filter_source_interface_id",
    )
    destination_interface_id = django_filters.ModelMultipleChoiceFilter(
        label=_("Destination Interface"),
        queryset=Interfaces.objects.all(),  # users pick real Interface rows
        method="filter_destination_interface_id",
    )
    interface = django_filters.ModelMultipleChoiceFilter(
        label=_("Interface"),
        queryset=Interfaces.objects.all(),
        method="filter_interface",
    )
    zone = django_filters.ModelMultipleChoiceFilter(
        label=_("Zone"),
        queryset=Zone.objects.all(),
        method="filter_zone",
    )
    

    class Meta:
        model = Policy
        fields = [
            'id', 'policyid', 'fortigate_id', 'comments', 'is_decommissioned', 'name', 
        ]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = Q(name__icontains=value)
        try:
            policyid = int(value)
            qs_filter |= Q(policyid=policyid)
        except (TypeError, ValueError):
            pass
        return queryset.filter(qs_filter)

    def _normalize_ids(self, value):
        # value can be a QS, list of model instances, or list of raw IDs
        if hasattr(value, "values_list"):
            return list(value.values_list("pk", flat=True))
        return [getattr(v, "pk", v) for v in value if v is not None]

    def filter_source_interface_id(self, qs, name, value):
        ids = self._normalize_ids(value)
        if not ids:
            return qs
        
        iface_qs = Interfaces.objects.filter(pk__in=ids).only("pk", "zones")
        zone_ids     = list(iface_qs.exclude(zones__isnull=True).values_list("zones", flat=True))
        iface_nozone = list(iface_qs.filter(zones__isnull=True).values_list("pk", flat=True))

        ct_zone  = ContentType.objects.get_for_model(Zone)
        ct_iface = ContentType.objects.get_for_model(Interfaces)

        return qs.filter(
            Q(source_interface__object_type=ct_zone,  source_interface__object_id__in=zone_ids) |
            Q(source_interface__object_type=ct_iface, source_interface__object_id__in=iface_nozone)
        ).distinct()

    def filter_destination_interface_id(self, qs, name, value):
        ids = self._normalize_ids(value)
        if not ids:
            return qs
        iface_qs = Interfaces.objects.filter(pk__in=ids).only("pk", "zones")
        zone_ids     = list(iface_qs.exclude(zones__isnull=True).values_list("zones", flat=True))
        iface_nozone = list(iface_qs.filter(zones__isnull=True).values_list("pk", flat=True))

        ct_zone  = ContentType.objects.get_for_model(Zone)
        ct_iface = ContentType.objects.get_for_model(Interfaces)

        return qs.filter(
            Q(destination_interface__object_type=ct_zone,  destination_interface__object_id__in=zone_ids) |
            Q(destination_interface__object_type=ct_iface, destination_interface__object_id__in=iface_nozone)
        ).distinct()


    def filter_interface(self, qs, name, value):
        ids = self._normalize_ids(value)
        if not ids:
            return qs
        iface_qs = Interfaces.objects.filter(pk__in=ids).only("pk", "zones")
        zone_ids     = list(iface_qs.exclude(zones__isnull=True).values_list("zones", flat=True))
        iface_nozone = list(iface_qs.filter(zones__isnull=True).values_list("pk", flat=True))

        ct_zone  = ContentType.objects.get_for_model(Zone)
        ct_iface = ContentType.objects.get_for_model(Interfaces)

        return qs.filter(
            Q(source_interface__object_type=ct_zone,  source_interface__object_id__in=zone_ids) |
            Q(source_interface__object_type=ct_iface, source_interface__object_id__in=iface_nozone) |
            Q(destination_interface__object_type=ct_zone,  destination_interface__object_id__in=zone_ids) |
            Q(destination_interface__object_type=ct_iface, destination_interface__object_id__in=iface_nozone)
        ).distinct()
    
    def filter_zone(self, qs, name, value):
        ids = self._normalize_ids(value)
        if not ids:
            return qs
        ct = ContentType.objects.get_for_model(Zone)
        return qs.filter(
            Q(source_interface__object_type=ct, source_interface__object_id__in=ids) |
            Q(destination_interface__object_type=ct, destination_interface__object_id__in=ids) 
        ).distinct()




class ProfileGroupFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = ProfileGroup
        fields = ("q", "fortigate_id", "is_decommissioned")


class UserGroupFilterSet(NetBoxModelFilterSet):
    fortigate_id = django_filters.NumberFilter(field_name="fortigate_id")
    is_decommissioned = django_filters.BooleanFilter(field_name="is_decommissioned")

    class Meta:
        model = UserGroup
        fields = ("q", "fortigate_id", "is_decommissioned")