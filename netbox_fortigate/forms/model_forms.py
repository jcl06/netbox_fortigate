from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device
from ipam.models import IPAddress
from netbox.forms import NetBoxModelForm


from ..models import *
from ..choices import (
    ScheduleModeChoices,
    ScheduleFrequencyChoices,
)


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

    


class FortiGateSchedulerForm(forms.ModelForm):
    interval_minutes = forms.IntegerField(
        required=False,
        min_value=1,
        label=_("Interval"),
        help_text=_("Used only for 'Every N minutes'. Example: 15 means run every 15 minutes."),
    )
    day_of_month = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=31,
        label=_("Day of month"),
        help_text=_("Required for monthly schedules (1-31). If a month is shorter, the job will run on the month's last day."),
    )
    class Meta:
        model = FortiGateScheduler
        fields = (
            "name",
            "description",
            "enabled",
            "job_type",
            "schedule_mode",
            "interval_minutes",
            "frequency",
            "time_of_day",
            "weekday",
            "day_of_month",
        )
        

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Determine selection from POST first, else instance
        mode = (self.data.get("schedule_mode") or getattr(self.instance, "schedule_mode", None) or ScheduleModeChoices.CRON)
        freq = (self.data.get("frequency") or getattr(self.instance, "frequency", None))

        # Always start from permissive requirements; enforce in clean()
        self.fields["interval_minutes"].required = False
        self.fields["frequency"].required = False
        self.fields["time_of_day"].required = False
        self.fields["weekday"].required = False
        self.fields["day_of_month"].required = False

        # Make UI clearer (optional)
        self.fields["interval_minutes"].widget.attrs.setdefault("placeholder", "e.g. 15")
        self.fields["time_of_day"].widget.attrs.setdefault("placeholder", "HH:MM (24h), e.g. 01:00")

