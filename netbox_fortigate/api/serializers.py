from rest_framework import serializers

from ..models import *



class _BaseEventSerializer(serializers.ModelSerializer):
    """
    Minimal serializer used for NetBox event/change serialization.

    IMPORTANT:
    - Use DRF ModelSerializer (NOT NetBoxModelSerializer) to avoid requiring API routes
      for hyperlinked `url` fields.
    """
    class Meta:
        fields = "__all__"


class FortigateSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Fortigate



class InterfacesSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Interfaces


class ZoneSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Zone


class RoutingTableSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = RoutingTable


class ObjectSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Object


class SchedulerSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Scheduler



class AddressSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Address


class AddressGroupSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = AddressGroup


class ServicesSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Services


class ServiceGroupSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = ServiceGroup


class VIPSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = VIP


class VIPGroupSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = VIPGroup


class ScheduleOnetimeSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = ScheduleOnetime


class ScheduleRecurringSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = ScheduleRecurring


class ScheduleGroupSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = ScheduleGroup


class UserSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = User


class AuthenticationServerSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = AuthenticationServer


class PolicySerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = Policy


class ProfileGroupSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = ProfileGroup


class UserGroupSerializer(_BaseEventSerializer):
    class Meta(_BaseEventSerializer.Meta):
        model = UserGroup