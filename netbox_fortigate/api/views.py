from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets
from .. import models
from . import serializers



class FortigateViewSet(NetBoxModelViewSet):
    queryset = models.Fortigate.objects.select_related("device").all()
    serializer_class = serializers.FortigateSerializer
    filterset_class =  filtersets.FortigateFilterSet


class InterfacesViewSet(NetBoxModelViewSet):
    queryset = models.Interfaces.objects.select_related("fortigate__device", "parent").all()
    serializer_class = serializers.InterfacesSerializer
    filterset_class =  filtersets.InterfacesFilterSet


class ZoneViewSet(NetBoxModelViewSet):
    queryset = models.Zone.objects.select_related("fortigate__device").prefetch_related("interface").all()
    serializer_class = serializers.ZoneSerializer
    filterset_class =  filtersets.ZoneFilterSet



class RoutingTableViewSet(NetBoxModelViewSet):
    queryset = models.RoutingTable.objects.select_related("fortigate__device", "interface", "next_hop").all()
    serializer_class = serializers.RoutingTableSerializer
    filterset_class =  filtersets.RoutingTableFilterSet


class ObjectViewSet(NetBoxModelViewSet):
    queryset = models.Object.objects.select_related("fortigate__device", "object_type").all()
    serializer_class = serializers.ObjectSerializer
    filterset_class =  filtersets.ObjectFilterSet


class SchedulerViewSet(NetBoxModelViewSet):
    queryset = models.Scheduler.objects.all()
    serializer_class = serializers.SchedulerSerializer
    filterset_class = filtersets.SchedulerFilterSet


class PolicyViewSet(NetBoxModelViewSet):
    queryset = models.Policy.objects.all()
    serializer_class = serializers.PolicySerializer
    filterset_class = filtersets.PolicyFilterSet