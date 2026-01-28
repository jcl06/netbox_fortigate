from django import forms

from dcim.models import Device
from ipam.models import IPAddress
from netbox.forms import NetBoxModelForm


from ..models import *

__all__ = (
 "FortiGateDeviceForm",
 "FortiGateSchedulerForm"
)

class FortiGateDeviceForm(NetBoxModelForm):
    device = forms.ModelChoiceField(
        queryset=Device.objects.all()
    )
    role = forms.CharField(required=False)
    mgmt_ip = forms.ModelChoiceField(queryset=IPAddress.objects.all(), required=False)

    class Meta:
        model = FortiGateDevice
        fields = (
            "device",
            "mgmt_ip",
            "description",
            "tags",
            "enabled",
            "role",
            "priority",
            "default_vdom",
            "api_port",
            "ssh_port",
            "fortios_version",
            "comments",
        )

    



class FortiGateSchedulerForm(NetBoxModelForm):
    class Meta:
        model = FortiGateScheduler
        fields = (
            "name",
            "enabled",
            "frequency",
            "time_of_day",
            "weekday",
            "day_of_month",
            "tags",
        )

    def clean(self):
        cleaned = super().clean()
        # Model.clean() handles frequency-specific validation too
        return cleaned
    


# class FortiGateInterfaceForm(NetBoxModelForm):
#     fortigate = forms.ModelChoiceField(queryset=FortiGateDevice.objects.all())
#     parent = forms.ModelChoiceField(queryset=FortiGateInterface.objects.none(), required=False)

#     class Meta:
#         model = FortiGateInterface
#         fields = (
#             "fortigate",
#             "name",
#             "description",
#             "tags",
#             "enabled",
#             "ip",
#             "type",
#             "role",
#             "parent",
#             "vdom",
#             "status",
#             "comments",
#         )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         fg = None
#         if getattr(self.instance, "pk", None):
#             fg = self.instance.fortigate
#         else:
#             fg_id = self.data.get("fortigate")
#             if fg_id:
#                 try:
#                     fg = FortiGateDevice.objects.get(pk=fg_id)
#                 except FortiGateDevice.DoesNotExist:
#                     fg = None

#         if fg:
#             self.fields["parent"].queryset = FortiGateInterface.objects.filter(fortigate=fg)
#         else:
#             self.fields["parent"].queryset = FortiGateInterface.objects.none()


# class FortiGateZoneForm(NetBoxModelForm):
#     fortigate = forms.ModelChoiceField(queryset=FortiGateDevice.objects.all())
#     interface = forms.ModelMultipleChoiceField(queryset=FortiGateInterface.objects.none(), required=False)

#     class Meta:
#         model = FortiGateZone
#         fields = (
#             "fortigate",
#             "name",
#             "type",
#             "intrazone",
#             "interface",
#             "description",
#             "comments",
#             "tags",
#         )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         fg = None
#         if getattr(self.instance, "pk", None):
#             fg = self.instance.fortigate
#         else:
#             fg_id = self.data.get("fortigate")
#             if fg_id:
#                 try:
#                     fg = FortiGateDevice.objects.get(pk=fg_id)
#                 except FortiGateDevice.DoesNotExist:
#                     fg = None

#         if fg:
#             self.fields["interface"].queryset = FortiGateInterface.objects.filter(fortigate=fg)
#         else:
#             self.fields["interface"].queryset = FortiGateInterface.objects.none()





