from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets
from .. import models
from . import serializers



class FortiGateDeviceViewSet(NetBoxModelViewSet):
    queryset = models.FortiGateDevice.objects.select_related("device").all()
    serializer_class = serializers.FortiGateDeviceSerializer
    filterset_class =  filtersets.FortiGateDeviceFilterSet


class FortiGateInterfaceViewSet(NetBoxModelViewSet):
    queryset = models.FortiGateInterface.objects.select_related("fortigate__device", "parent").all()
    serializer_class = serializers.FortiGateInterfaceSerializer
    filterset_class =  filtersets.FortiGateInterfaceFilterSet


# class FortiGateZoneViewSet(NetBoxModelViewSet):
#     queryset = models.FortiGateZone.objects.select_related("fortigate__device").prefetch_related("interface").all()
#     serializer_class = serializers.FortiGateZoneSerializer
#     filterset_class =  filtersets.FortiGateZoneFilterSet



class FortiGateRouteViewSet(NetBoxModelViewSet):
    queryset = models.FortiGateRoute.objects.select_related("fortigate__device", "interface", "next_hop").all()
    serializer_class = serializers.FortiGateRouteSerializer
    filterset_class =  filtersets.FortiGateRouteFilterSet


# class FortiGateObjectViewSet(NetBoxModelViewSet):
#     queryset = models.FortiGateObject.objects.select_related("fortigate__device", "object_type").all()
#     serializer_class = serializers.FortiGateObjectSerializer
#     filterset_class =  filtersets.FortiGateObjectFilterSet