from django.utils.translation import gettext_lazy as _
from django import forms

from dcim.models import Device
from ipam.models import IPAddress
from netbox.forms import NetBoxModelImportForm
from utilities.forms.fields import CSVModelChoiceField

from ..models import Fortigate, default_api_port, default_ssh_port

__all__ = (
    'FortigateImportForm',
)


class FortigateImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=True,
        to_field_name='name',
        help_text=_('Device')
    )

    mgmt_ip = CSVModelChoiceField(
        label=_('Management IP'),
        queryset=IPAddress.objects.all(),
        required=False,
        to_field_name='address',
        help_text=_('Device Management IP Address')
    )
    priority = forms.IntegerField(
        required=False,
        initial=1,
        help_text=_('Priority')
    )
    api_port = forms.IntegerField(
        required=False,
        initial=default_api_port(),
        help_text=_('API Port')
    )
    ssh_port = forms.IntegerField(
        required=False,
        initial=default_ssh_port(),
        help_text=_('SSH Port')
    )
    default_vdom = forms.CharField(
        required=False,
        initial="root",
        help_text=_('Default VDOM')
    )
    role = forms.CharField(
        required=False,
        initial="firewall",
        help_text=_('Fortigate plugin role key (e.g. user_vpn).')
    )


    class Meta:
        model = Fortigate
        fields = (
            "device",
            "mgmt_ip",
            "description",
            "role",
            "priority",
            "default_vdom",
            "api_port",
            "ssh_port",
            "fortios_version",
        )

