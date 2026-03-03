from netbox.api.serializers import NetBoxModelSerializer

from ..models import *


class FortigateSerializer(NetBoxModelSerializer):
    class Meta:
        model = Fortigate
        fields = "__all__"



class InterfacesSerializer(NetBoxModelSerializer):
    class Meta:
        model = Interfaces
        fields = "__all__"


# class ZoneSerializer(NetBoxModelSerializer):
#     class Meta:
#         model = Zone
#         fields = "__all__"


class RoutingTableSerializer(NetBoxModelSerializer):
    class Meta:
        model = RoutingTable
        fields = "__all__"


# class ObjectSerializer(NetBoxModelSerializer):
#     class Meta:
#         model = Object
#         fields = "__all__"


class SchedulerSerializer(NetBoxModelSerializer):
    class Meta:
        model = Scheduler
        fields = "__all__"



class PolicySerializer(NetBoxModelSerializer):
    class Meta:
        model = Policy
        fields = "__all__"