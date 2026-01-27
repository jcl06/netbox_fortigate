

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from netbox.models import PrimaryModel

from ..choices import CONTENT_TYPE_CHOICES, OBJECT_TYPE_CHOICES


__all__ = (
    "FortiGateObject",
)

class FortiGateObject(PrimaryModel):
    name = models.CharField(max_length=255, blank=True, null=True, editable=False)

    object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=CONTENT_TYPE_CHOICES,
    )
    object_id = models.PositiveBigIntegerField()

    fortigate = models.ForeignKey(
        to='netbox_fortigate.FortiGateDevice',
        on_delete=models.PROTECT,
        related_name="fortigate_objects",
    )

    type = models.CharField(
        choices=OBJECT_TYPE_CHOICES,
        blank=True,
        null=True,
        max_length=64,
    )

    enabled = models.BooleanField(default=True)

    object = GenericForeignKey("object_type", "object_id")

    class Meta:
        ordering = ("fortigate__device__name", "type", "name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("fortigate", "object_type", "object_id"),
                name="uniq_fortigate_object_target",
            ),
        ]
        verbose_name = _("FortiGate Object")
        verbose_name_plural = _("FortiGate Objects")

    def __str__(self):
        if self.object and getattr(self.object, "name", None):
            return f"{self.object_type.model.upper()} ({self.fortigate.device}) - {self.name}"
        return str(self.pk)

    def clean(self):
        super().clean()

        if not self.object_type_id or not self.object_id:
            return

        model = self.object_type.model_class()
        if model is None:
            raise ValidationError({"object_type": _("Invalid content type.")})

        try:
            target = model.objects.get(pk=self.object_id)
        except model.DoesNotExist:
            raise ValidationError({"object_id": _("Referenced object does not exist.")})

        # Enforce: target belongs to same FortiGateDevice when target has fortigate_id
        target_fg_id = getattr(target, "fortigate_id", None)
        if target_fg_id is not None and self.fortigate_id and target_fg_id != self.fortigate_id:
            raise ValidationError({"fortigate": _("Referenced object belongs to a different FortiGate.")})

    def save(self, *args, **kwargs):
        # keep legacy behavior: infer type/name/device-ish from target
        if self.object_type_id and self.object_id:
            model = self.object_type.model_class()
            if model:
                target = model.objects.filter(pk=self.object_id).first()
                if target is not None:
                    # legacy stored 'type' from content type name; keep it stable
                    self.type = self.type or self.object_type.name
                    if getattr(target, "name", None):
                        self.name = target.name
                    if getattr(target, "fortigate_id", None) and not self.fortigate_id:
                        self.fortigate_id = target.fortigate_id

        super().save(*args, **kwargs)

    def intf_obj_with_any(self):
        objs = [self]
        any_obj = FortiGateObject.objects.filter(
            fortigate=self.fortigate,
            name="any",
            enabled=True,
        ).first()
        if any_obj and any_obj.pk != self.pk:
            objs.append(any_obj)
        return objs

    