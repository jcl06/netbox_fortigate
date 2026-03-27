from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory, TypedChoiceField

from ..models.request import Request, FirewallRequest
from .fields import FreeformMultipleChoiceField


class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = (
            "remarks",
        )


class FirewallRequestForm(forms.ModelForm):
    source = FreeformMultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.SelectMultiple(
            attrs={
                "class": "tomselect-multi",
            }
        ),
    )
    destination = FreeformMultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.SelectMultiple(
            attrs={
                "class": "tomselect-multi",
            }
        ),
    )
    protocol = forms.TypedChoiceField(
        required=False,
        choices=(('', 'Select a Protocol'), ('tcp', 'TCP'), ('udp', 'UDP'), ('icmp', 'ICMP')),
    )
    ports = FreeformMultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.SelectMultiple(
            attrs={
                "class": "tomselect-multi",
            }
        ),
    )
    username = FreeformMultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.SelectMultiple(
            attrs={
                "class": "tomselect-multi",
            }
        ),
    )

    class Meta:
        model = FirewallRequest
        fields = ("source", "destination", "protocol", "ports", "username")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ("source", "destination", "ports", "username"):
            self._seed_field_choices(field_name)

    def _seed_field_choices(self, field_name):
        values = []

        if self.is_bound:
            values.extend(self.data.getlist(self.add_prefix(field_name)))

        instance_value = getattr(self.instance, field_name, None)
        if isinstance(instance_value, list):
            values.extend(instance_value)

        initial_value = self.initial.get(field_name)
        if isinstance(initial_value, list):
            values.extend(initial_value)

        normalized = []
        seen = set()
        for v in values:
            v = str(v).strip()
            if v and v not in seen:
                normalized.append(v)
                seen.add(v)

        self.fields[field_name].choices = [(v, v) for v in normalized]
        self.initial[field_name] = normalized


class BaseFirewallRequestInlineFormSet(BaseInlineFormSet):
    pass


FirewallRequestFormSet = inlineformset_factory(
    Request,
    FirewallRequest,
    form=FirewallRequestForm,
    formset=BaseFirewallRequestInlineFormSet,
    extra=0,
    can_delete=True,
)