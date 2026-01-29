from netbox.api.serializers import NetBoxModelSerializer

from ..models import *


class FortiGateDeviceSerializer(NetBoxModelSerializer):
    class Meta:
        model = FortiGateDevice
        fields = "__all__"



class FortiGateInterfaceSerializer(NetBoxModelSerializer):
    class Meta:
        model = FortiGateInterface
        fields = "__all__"


# class FortiGateZoneSerializer(NetBoxModelSerializer):
#     class Meta:
#         model = FortiGateZone
#         fields = "__all__"


class FortiGateRouteSerializer(NetBoxModelSerializer):
    class Meta:
        model = FortiGateRoute
        fields = "__all__"


# class FortiGateObjectSerializer(NetBoxModelSerializer):
#     class Meta:
#         model = FortiGateObject
#         fields = "__all__"


class FortiGateSchedulerSerializer(NetBoxModelSerializer):
    class Meta:
        model = FortiGateScheduler
        fields = "__all__"
