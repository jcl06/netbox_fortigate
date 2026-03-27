from django import forms


from django import forms


class FreeformMultipleChoiceField(forms.MultipleChoiceField):
    def validate(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages["required"], code="required")

    def valid_value(self, value):
        return True

    def clean(self, value):
        value = forms.Field.clean(self, value)
        if not value:
            return []
        return [str(v).strip() for v in value if str(v).strip()]