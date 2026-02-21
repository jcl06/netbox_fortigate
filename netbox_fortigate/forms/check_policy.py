import ipaddress
from django import forms


class CheckPolicyForm(forms.Form):
    src = forms.CharField(required=True)
    dst = forms.CharField(required=True)
    protocol = forms.ChoiceField(choices=[("icmp", "ICMP"), ("tcp", "TCP"), ("udp", "UDP")], required=True)
    port = forms.IntegerField(required=False, min_value=1, max_value=65535)
    username = forms.CharField(required=False)

    def clean_src(self):
        value = self.cleaned_data["src"].strip()
        ipaddress.ip_address(value)
        return value

    def clean_dst(self):
        value = self.cleaned_data["dst"].strip()
        ipaddress.ip_address(value)
        return value

    def clean(self):
        cleaned = super().clean()
        protocol = cleaned.get("protocol")
        port = cleaned.get("port")

        if protocol != "icmp" and not port:
            raise forms.ValidationError("Port is required for TCP/UDP.")
        if protocol == "icmp":
            # allow blank or a type number; if blank, your backend can treat as ALL_ICMP if desired
            # if you always want type 8 default, do it here:
            cleaned["port"] = port or 8

        return cleaned