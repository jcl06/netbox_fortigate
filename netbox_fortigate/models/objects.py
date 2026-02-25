
import ipaddress
import re

from django.db.models import Q
from django.db import models
from django.utils import timezone
from datetime import datetime
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from netbox.models import PrimaryModel
from ipam.fields import IPNetworkField

from ..fields import HostAddressField
from ..choices import *


__all__ = (
    'Object',
    'Address',
    'AddressGroup',
    'Services',
    'ServiceGroup',
    'VIP',
    'VIPGroup',
    'ScheduleOnetime',
    'ScheduleRecurring',
    'ScheduleGroup',
    'User',
    'AuthenticationServer'
)


class Object(PrimaryModel):
    name = models.CharField(max_length=255, blank=True, null=True, editable=False)

    object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=CONTENT_TYPE_CHOICES,
    )
    object_id = models.PositiveBigIntegerField()

    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
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
        verbose_name = _("Object")
        verbose_name_plural = _("Objects")

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

        # Enforce: target belongs to same Fortigate when target has fortigate_id
        target_fg_id = getattr(target, "fortigate_id", None)
        if target_fg_id is not None and self.fortigate_id and target_fg_id != self.fortigate_id:
            raise ValidationError({"fortigate": _("Referenced object belongs to a different Fortigate.")})

    def save(self, *args, **kwargs):
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
        any_obj = Object.objects.filter(
            fortigate=self.fortigate,
            name="any",
            enabled=True,
        ).first()
        if any_obj and any_obj.pk != self.pk:
            objs.append(any_obj)
        return objs

    
    
class Address(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=79,
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    type = models.CharField(
        verbose_name=_('type'),
        max_length=16,
        choices=ADDRESS_TYPE_CHOICES,
        default='ipmask',
        help_text='Type of address.'
    )
    subnet = IPNetworkField(
        verbose_name=_('subnet'),
        help_text=_('IPv4 network with mask'),
        blank=True,
        null=True,
        default='',
    )
    start_ip = HostAddressField(
        verbose_name=_('Start-IP'),
        blank=True,
        null=True,
        default='',
        help_text=_('First IP address (inclusive) in the range for the address.')
    )
    end_ip = HostAddressField(
        verbose_name=_('End-IP'),
        blank=True,
        null=True,
        default='',
        help_text=_('Final IP address (inclusive) in the range for the address.')
    )
    fqdn = models.CharField(
        verbose_name=_('FQDN'),
        max_length=255,
        blank=True,
        default='',
        help_text='Fully Qualified Domain Name address.'
    )
    interface = models.CharField(
        verbose_name=_('interface'),
        max_length=35,
        blank=True,
        default='',
        help_text='Name of interface whose IP address is to be used.'
    )
    comment = models.TextField(
        verbose_name=_('comment'),
        blank=True,
        null=True
    )

    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name_plural = _('addresses')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            Address.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            AddressGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        

        if self.type == 'ipmask' and not self.subnet:
            raise ValidationError({'subnet': 'Please ensure Subnet is not empty'})

        if self.type == 'iprange' and (not self.start_ip or not self.end_ip):
            raise ValidationError({
                'start_ip': 'Please ensure Start IP is not empty.',
                'end_ip': 'Please ensure End IP is not empty.'
        })
        
        if self.type == 'fqdn' and not self.fqdn:
            raise ValidationError({'fqdn': 'Please ensure FQDN is not empty'})
        
        if self.type == 'iprange' and self.start_ip and self.end_ip:
            if ipaddress.ip_address(self.start_ip) > ipaddress.ip_address(self.end_ip):
                raise ValidationError({
                    'start_ip': 'Start IP cannot be greater than End IP.'
        })
        
        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class AddressGroup(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=79,
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    type = models.CharField(
        verbose_name=_('type'),
        max_length=7,
        choices=(('default', 'Group'), ('folder', 'Folder')),
        default='default',
        help_text='Address group type.'
    )
    member = models.ManyToManyField(
        verbose_name=_('member'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['address', 'address group']},
        related_name='%(class)s_member',
        help_text='Address objects contained within the group.'
    )
    comment = models.TextField(
        verbose_name=_('comment'),
        blank=True,
        null=True
    )

    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('address group')
        verbose_name_plural = _('address groups')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            AddressGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            Address.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        
        # Ensure members belong to the same fortigate
        if self.pk and self.member.exists() and self.member.exclude(fortigate=self.fortigate).exists():
            raise ValidationError({'member': 'All members must belong to the same fortigate.'})
        
        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class Services(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=79,
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    # Protocol allowed from Fortinet
    # TCP/UDP/UDP-Lite/SCTP, ICMP, ICMP6, IP. HTTP, FTP, CONNECT, SOCKS-TCP, SOCKS-UDP, ALL
    protocol = models.CharField(
        verbose_name=_('protocol'),
        max_length=22,
        choices=ServiceProtocolChoices,
        help_text=_('Protocol type'),
        default=ServiceProtocolChoices.DEFAULT,
    )
    # For IP protocol only
    protocol_number = models.PositiveSmallIntegerField(
        verbose_name=_('protocol-number'),
        blank=True,
        null=True,
        default=None,
        help_text=_('IP protocol number.')
    )
    # For ICMP protocol only
    icmptype = models.PositiveBigIntegerField(
        verbose_name=_('ICMP Type'),
        blank=True,
        null=True,
        default=None,
        validators=[MinValueValidator(0), MaxValueValidator(4294967295)],
        help_text=_('ICMP type.')
    )
    # For TCP/UDP/UDP-Lite/SCTP
    tcp_portrange = models.TextField(
        verbose_name=_('TCP Port Range'),
        blank=True,
        default='',
        help_text='Multiple TCP port ranges.'
    )
    # For TCP/UDP/UDP-Lite/SCTP
    udp_portrange = models.TextField(
        verbose_name=_('UDP Port Range'),
        blank=True,
        default='',
        help_text='Multiple UDP port ranges.'
    )
    comment = models.TextField(
        verbose_name=_('comment'),
        blank=True,
        null=True
    )

    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('service')
        verbose_name_plural = _('services')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            Services.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            ServiceGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.protocol_number == '':
            self.protocol_number = None
        super().clean()
        
        if self.protocol == ServiceProtocolChoices.DEFAULT and not (self.tcp_portrange or self.udp_portrange):
            raise ValidationError('Please ensure at least one of TCP Port or UDP Port is not empty.')
            
        if self.protocol == ServiceProtocolChoices.IP and self.protocol_number is None:
            raise ValidationError({'protocol_number': 'Please ensure Protocol Number is not empty.'})
        
        if self.tcp_portrange:
            self.validate_portrange(self.tcp_portrange)
        if self.udp_portrange:
            self. validate_portrange(self.udp_portrange)
        
        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})
        
    def validate_portrange(self, value):
        # Regular expression pattern to match valid port numbers and ranges with optional source ports
        pattern = re.compile(r'^(?:\d{1,5}(?:-\d{1,5})?(?::\d{1,5}(?:-\d{1,5})?)?)(?:\s+\d{1,5}(?:-\d{1,5})?(?::\d{1,5}(?:-\d{1,5})?)?)*$')

        # Check if the value matches the pattern
        if not pattern.fullmatch(value):
            raise ValidationError("Invalid port range format. Use numbers or ranges (e.g., 20 21 or 20-21 or 80 443 20-21). Numbers must be between 0 and 65535.")

        # Validate each part of the input
        for part in value.split():
            segments = part.split(':')
            
            for segment in segments:
                if '-' in segment:
                    start, end = segment.split('-')
                    try:
                        start, end = int(start), int(end)
                        if not (0 <= start <= 65535 and 0 <= end <= 65535 and start <= end):
                            raise ValidationError("Port range values must be between 0 and 65535, and start cannot be greater than end.")
                    except ValueError:
                        raise ValidationError("Port range values must be integers.")
                else:
                    try:
                        port = int(segment)
                        if port < 0:
                            raise ValidationError("Port 0 is not allowed unless used in a range (e.g., 0-10).")
                        if not (0 <= port <= 65535):
                            raise ValidationError("Port numbers must be between 0 and 65535.")
                    except ValueError:
                        raise ValidationError("Port numbers must be integers.")


class ServiceGroup(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=79,
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    member = models.ManyToManyField(
        verbose_name=_('member'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['service', 'service group']},
        related_name='%(class)s',
        help_text='Service and service group names.',
    )
    comment = models.TextField(
        verbose_name=_('comment'),
        blank=True,
        null=True
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('service group')
        verbose_name_plural = _('service groups')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            ServiceGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            Services.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Ensure members belong to the same fortigate
        if self.pk and self.member.exists() and self.member.exclude(fortigate=self.fortigate).exists():
            raise ValidationError({'member': 'All members must belong to the same fortigate.'})
        
        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class VIP(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=79,
        help_text=_('Virtual IP name.')
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    type = models.CharField(
        verbose_name=_('type'),
        max_length=19,
        choices=VIP_TYPE_CHOICES,
        default='static-nat',
        help_text='Configure a static NAT, load balance, server load balance, access proxy, DNS translation, or FQDN VIP.'
    )
    src_filter = ArrayField(
        base_field=models.CharField(max_length=79),
        verbose_name=_('Source Address'),
        blank=True,
        default=list,
        help_text='Source address filter. Each address must be either an IP/subnet (x.x.x.x/n) or a range (x.x.x.x-y.y.y.y). Separate addresses with spaces.'
    )
    service = ArrayField(
        base_field=models.CharField(max_length=79),
        verbose_name=_('service'),
        blank=True,
        default=list,
        help_text='Service and service group names.'
    )
    external_ip = models.CharField(
        verbose_name=_('External IP'),
        max_length=33,
        null=True,
        blank=True,
        default='',
        help_text='IP address or address range on the external interface that you want to map to an address or address range on the destination network.'
    )
    external_address = models.ForeignKey(
        verbose_name=_('External Address'),
        to='netbox_fortigate.Address',
        on_delete=models.PROTECT,
        limit_choices_to={'is_decommissioned': False},
        related_name='%(class)s_external_address',
        blank=True,
        null=True,
        help_text='External FQDN address name.',
    )
    mapped_ip = models.CharField(
        verbose_name=_('Mapped IP'),
        max_length=33,
        blank=True,
        null=True,
        default='',
        help_text='IP address or address range on the destination network to which the external IP address is mapped.'
    )
    mapped_address = models.ForeignKey(
        to='netbox_fortigate.Address',
        verbose_name=_('Mapped FQDN Address'),
        on_delete=models.PROTECT,
        limit_choices_to={'is_decommissioned': False},
        related_name='%(class)s',
        blank=True,
        null=True,
        help_text='Mapped FQDN address name.',
    )
    external_interface = models.CharField(
        verbose_name=_('External Interface'),
        max_length=15,
        default='any',
        help_text='Interface connected to the source network that receives the packets that will be forwarded to the destination network.'
    )
    port_forward = models.CharField(
        verbose_name=_('Port Forwarding'),
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='enable',
        help_text='Enable/disable port forwarding.'
    )
    status = models.CharField(
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='enable',
        help_text='Enable/disable VIP.'
    )
    protocol = models.CharField(
        max_length=4,
        choices=PORT_FORWARDING_PROTOCOL_CHOICES,
        default='tcp',
        help_text='Protocol to use when forwarding packets.'
    )
    external_port = models.CharField(
        verbose_name=_('External Port'),
        max_length=11,
        default='0-65535',
        help_text='Protocol to use when forwarding packets.'
    )
    mapped_port = models.CharField(
        verbose_name=_('Mapped Port'),
        max_length=11,
        default='0-65535',
        help_text='Port number range on the destination network to which the external port number range is mapped.'
    )
    portmapping_type = models.CharField(
        max_length=7,
        choices=(('1-to-1', 'One to one'), ('m-to-n', 'Many to many')),
        default='1-to-1',
        help_text='Enable/disable VIP.'
    )
    comment = models.TextField(
        verbose_name=_('comment'),
        blank=True,
        null=True
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('Virtual IP')
        verbose_name_plural = _('Virtual IPs')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            VIP.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            VIPGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()


        if self.type == 'static-nat' and not self.mapped_ip:
            raise ValidationError({'mapped_ip': 'Please ensure Mapped IP is not empty'})

        if self.type == 'fqdn' and not self.mapped_address:
            raise ValidationError({'mapped_address': 'Please ensure Mapped Address is not empty'})
        

        if self.type == 'fqdn' and (self.external_ip == '0.0.0.0' or not self.external_ip) and not self.external_address:
            raise ValidationError({
                '__all__': 'Please ensure External IP/Address is not empty',
                'external_address': 'Please ensure External Address is not empty',
                'external_ip': 'Please ensure External IP is not empty'
            })
        
        
        if self.external_address and self.mapped_address:
            if self.external_address == self.mapped_address:
                ValidationError({
                    'external_address': 'External and Mapped Address should be not the same address',
                    'mapped_address': 'External and Mapped Address should be not the same address',
                })

        if isinstance(self.service, list) and self.fortigate:  # Since it's an ArrayField, check if it's a list
            for service_name in self.service:
                if not Object.objects.filter(name=service_name, is_decommissioned=False, fortigate=self.fortigate).exists():
                    raise ValidationError({'member': f'Member {service_name} does not exist or is decommissioned.'})
                
        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class VIPGroup(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=79,
        help_text=_('Virtual IP name.')
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    interface = models.CharField(
        verbose_name=_('External Interface'),
        max_length=15,
        default='any',
        help_text='Interface connected to the source network that receives the packets that will be forwarded to the destination network.'
    )
    member = models.ManyToManyField(
        verbose_name=_('Member'),
        to='netbox_fortigate.VIP',
        limit_choices_to={'is_decommissioned': False},
        related_name='%(class)s',
        help_text='External FQDN address name.',
    )

    comments = models.TextField(
        verbose_name=_('comments'),
        blank=True,
        null=True
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('Virtual IP Group')
        verbose_name_plural = _('Virtual IP Groups')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            VIPGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            VIP.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Ensure members belong to the same fortigate
        if self.pk and self.member.exists() and self.fortigate and self.member.exclude(external_interface=self.interface).exists():
            raise ValidationError({'member': 'All members must belong to the same interface.'})

        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class ScheduleOnetime(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=31,
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    start = models.DateTimeField(
        verbose_name=_('start'),
        help_text='Schedule start date and time, format hh:mm yyyy/mm/dd',
    )
    end = models.DateTimeField(
        verbose_name=_('end'),
        help_text='Schedule start date and time, format hh:mm yyyy/mm/dd',
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('schedule onetime')
        verbose_name_plural = _('schedule onetime')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            ScheduleOnetime.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            ScheduleRecurring.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
            or
            ScheduleGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )


    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Enforce datetime format 'hh:mm yyyy/mm/dd'
        date_format = '%H:%M %Y/%m/%d'

        for field in ['start', 'end']:
            value = getattr(self, field)
            if value:
                try:
                    # Convert string to datetime if it's not already
                    if isinstance(value, str):  
                        value = datetime.strptime(value, date_format)  

                    # Make the datetime timezone-aware
                    if timezone.is_naive(value):
                        value = timezone.make_aware(value, timezone.get_current_timezone())

                    setattr(self, field, value)
                except ValueError:
                    raise ValidationError({field: f'Invalid date format for {field}. Use "hh:mm yyyy/mm/dd".'})

        if self.start and self.end and self.start >= self.end:
            raise ValidationError({'end': 'End date must be after start date.'})

        if self.name and self.fortigate:
            if self.get_duplicate_name():
                raise ValidationError('Found duplicate name')
    


class ScheduleRecurring(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=31,
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    start = models.TimeField(
        verbose_name=_('start'),
        help_text='Time of day to start the schedule, format hh:mm.',
    )
    end = models.TimeField(
        verbose_name=_('end'),
        help_text='Time of day to end the schedule, format hh:mm.',
    )
    day = models.CharField(
        max_length=57,
        verbose_name=_('day'),
        default='none',
        help_text='One or more days of the week on which the schedule is valid.'
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('schedule recurring')
        verbose_name_plural = _('schedule recurring')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            ScheduleRecurring.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            ScheduleOnetime.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
            or
            ScheduleGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Ensure 'start' and 'end' are properly formatted
        for field in ['start', 'end']:
            value = getattr(self, field)
            if isinstance(value, str):
                try:
                    setattr(self, field, datetime.strptime(value, '%H:%M').time())
                except ValueError:
                    raise ValidationError({field: f'Invalid time format for {field}. Use "HH:MM".'})

        # Ensure start < end
        if self.start and self.end:
            if self.start > self.end:
                raise ValidationError({'end': 'End time must be after start time.'})
            elif self.start == self.end and self.start == datetime.strptime('00:00', '%H:%M').time():
                pass  # Allow 00:00 - 00:00 schedules (24-hour schedule)

        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class ScheduleGroup(PrimaryModel):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=31,
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    member = models.ManyToManyField(
        verbose_name=_('member'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['schedule onetime', 'schedule recurring']},
        related_name='%(class)s_member',
        help_text='Schedules added to the schedule group.'
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )
        verbose_name = _('schedule group')
        verbose_name_plural = _('schedule group')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'

    def get_duplicate_name(self):
        return (
            ScheduleGroup.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            ScheduleRecurring.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
            or
            ScheduleOnetime.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Ensure members belong to the same fortigate
        if self.pk and self.member.exists() and self.member.exclude(fortigate=self.fortigate).exists():
            raise ValidationError({'member': 'All members must belong to the same fortigate.'})
        
        # Check for duplicate name
        if self.name and self.fortigate and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})
        
    

class User(PrimaryModel):
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    name = models.CharField(
        max_length=64
    )

    type = models.CharField(
        verbose_name=_('Group Type'),
        max_length=20,
        choices=(('password', 'Local User'), ('radius', 'Remote RADIUS User'), ('tacacs+', 'Remote TACACS+ User'), ('ldap', 'Remote LDAP User')),
        default='password',
        help_text='Authentication method.'
    )
    status = models.CharField(
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='enable'
    )
    server = models.ForeignKey(
        to='netbox_fortigate.AuthenticationServer',
        verbose_name=_('authentication server'),
        on_delete=models.SET_NULL,
        related_name='%(class)s',
        blank=True,
        null=True,
        default=None,
        limit_choices_to={'is_decommissioned': False},
    ) 
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )

        verbose_name = _('user')
        verbose_name_plural = _('Users')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'
    
    def get_duplicate_name(self):
        return (
            User.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            AuthenticationServer.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        
        if self.type != 'password' and not self.server:
            raise ValidationError({'server': 'Please ensure server is not empty'})
        
        if self.type != 'password' and self.server.type != 'saml' and self.server and self.type != self.server.type:
            raise ValidationError({
                '__all__': 'Ensure server has the same type',
                'type': 'Please select group type with same type of the server',
                'server': 'Please select server with same type'
            })
        
        if self.type != 'password' and self.fortigate and self.fortigate != self.server.fortigate:
            raise ValidationError({'server': 'Please ensure server is belong to same fortigate'})
        
        if self.type == 'password' and self.server:
            raise ValidationError({'server': 'Please remove server for local group type'})
        
        # Check for duplicate name within the same fortigate
        if self.fortigate and self.name and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class AuthenticationServer(PrimaryModel):
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    name = models.CharField(
        max_length=35
    )
    type = models.CharField(
        verbose_name=_('Server Type'),
        max_length=20,
        choices=(('radius', 'RADIUS'), ('tacacs+', 'TACACS+'), ('ldap', 'LDAP'), ('saml', 'SAML')),
        default='password',
        help_text='Remote Authentication Type.'
    )
    server = models.CharField(
        max_length=63,
        blank=True,
        null=True,
        default='',
        verbose_name=_('server'),
        help_text=_('Primary server CN domain name or IP address.')
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)
    
    
    class Meta:
        ordering = ('fortigate', 'name')
        constraints = (
            models.UniqueConstraint(
                'name', 'fortigate', 'is_decommissioned',
                condition=Q(is_decommissioned=False),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )

        verbose_name = _('authentication server')
        verbose_name_plural = _('authentication servers')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'
    
    def get_duplicate_name(self):
        return (
            AuthenticationServer.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exclude(pk=self.pk).exists()
            or
            User.objects.filter(
                name=self.name, fortigate=self.fortigate, is_decommissioned=False
            ).exists()
        )

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Check for duplicate name within the same fortigate
        if self.fortigate and self.name and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})

