from django.apps import apps
from django.db.models import Q, Max
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from datetime import datetime
from ..fields import HostAddressField
from ..choices import *
from netbox.models import PrimaryModel
from .objects import Object, User, AuthenticationServer
from .devices import Fortigate
from ipaddress import ip_address, ip_network, IPv4Address, IPv4Network


__all__ = (
    'Policy',
    'ProfileGroup',
    'UserGroup'
)


class Policy(PrimaryModel):
    policyid = models.PositiveBigIntegerField(
        verbose_name=_('Policy ID'),
        validators=[MinValueValidator(1), MaxValueValidator(4294967294)],
        blank=True,
        null=True,
        default=None
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    status = models.CharField(
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='enable'
    )
    name = models.CharField(
        max_length=35,
        blank=True,
        default=''
    )
    source_interface = models.ManyToManyField(
        verbose_name='Source Interface',
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['zone', 'interface']},
        related_name='%(class)s_src_object',
        help_text='Incoming (ingress) interface.'
    )
    destination_interface = models.ManyToManyField(
        verbose_name=_('Destination Interface'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['zone', 'interface']},
        related_name='%(class)s_dst_object',
        help_text='Outgoing (egress) interface.'
    )
    action = models.CharField(
        max_length=10,
        choices=ActionChoices,
        default=ActionChoices.ACCEPT,
        help_text='Policy action (accept/deny/ipsec).'
    )
    '''nat64 = models.CharField(
        verbose_name=_('NAT64'),
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='disable',
        help_text='Enable/disable NAT64.',
    )
    nat46 = models.CharField(
        verbose_name=_('NAT46'),
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='disable',
        help_text='Enable/disable NAT46.',
    )'''
    source_address = models.ManyToManyField(
        verbose_name=_('Source Address'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['address', 'address group']},
        related_name='%(class)s_srcaddr_object',
        help_text='Source IPv4 addresses and groups',
    )
    destination_address = models.ManyToManyField(
        verbose_name=_('Destination Address'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['address', 'address group', 'Virtual IP', 'Virtual IP Group']},
        related_name='%(class)s_dstaddr_object',
        help_text='Destination IPv4 addresses and groups.',
    )
    schedule = models.ForeignKey(
        verbose_name=_('schedule'),
        to='netbox_fortigate.Object',
        on_delete=models.PROTECT,
        limit_choices_to={'is_decommissioned': False, 'type__in': ['schedule group', 'schedule onetime', 'schedule recurring']},
        related_name='%(class)s_schedule_object',
        blank=True,
        null=True,
    )
    service = models.ManyToManyField(
        verbose_name=_('service'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['service', 'service group']},
        related_name='%(class)s_service',
        help_text='Service and service group names.',
    )
    inspection_mode = models.CharField(
        verbose_name=_('inspection mode'),
        max_length=5,
        choices=(('flow', 'Flow'), ('proxy', 'Proxy')),
        default='flow',
        help_text='Policy inspection mode (Flow/proxy). Default is Flow mode.'
    )
    profile_type = models.CharField(
        verbose_name=_('profile type'),
        max_length=6,
        choices=(('single', 'Single'), ('group', 'Group')),
        default='single',
        help_text='Determine whether the firewall policy allows security profile groups or single profiles only.'
    )
    profile_group = models.ForeignKey(
        verbose_name=_('profile group'),
        to='netbox_fortigate.ProfileGroup',
        on_delete=models.PROTECT,
        limit_choices_to={'is_decommissioned': False},
        blank=True,
        null=True,
        related_name='%(class)s',
    )
    logging = models.CharField(
        verbose_name=_('logging'),
        max_length=7,
        choices=(('all', 'All'), ('utm', 'UTM'), ('disable', 'Disable')),
        default='all',
        help_text='Enable or disable logging. Log all sessions or security profile sessions.'
    )
    nat = models.CharField(
        verbose_name=_('NAT'),
        max_length=7,
        choices=NATChoices,
        default=NATChoices.DISABLE,
        help_text='Enable/disable source NAT.'
    )
    groups = models.ManyToManyField(
        verbose_name=_('groups'),
        to='netbox_fortigate.UserGroup',
        limit_choices_to={'is_decommissioned': False},
        blank=True,
        related_name='%(class)s',
        help_text='Names of user groups that can authenticate with this policy.'
    )
    users = models.ManyToManyField(
        verbose_name=_('users'),
        to='netbox_fortigate.User',
        limit_choices_to={'is_decommissioned': False},
        blank=True,
        related_name='%(class)s',
        help_text='Names of individual users that can authenticate with this policy.'
    )
    expiry = models.CharField(
        verbose_name=_('Policy Expiry'),
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='disable',
        help_text=_('Enable/disable policy expiry.')
    )
    expiry_date = models.DateTimeField(
        verbose_name=_('Expiry Date'),
        blank=True,
        null=True,
        default=None,
        help_text='Policy expiry date (hh:mm yyyy/mm/dd).',
    )
    comments = models.TextField(
        max_length=1023,
        blank=True,
        null=True
    )
    position = models.PositiveBigIntegerField(
        editable=False,
    )
    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ('fortigate', 'policyid')
        constraints = (
            models.UniqueConstraint(
                'policyid', 'fortigate', 'is_decommissioned',
                condition=(Q(is_decommissioned=False) & Q(policyid__isnull=False)),
                name='%(app_label)s_%(class)s_unique_policy'
            ),
            models.UniqueConstraint(
                'policyid', 'fortigate', 'name', 'is_decommissioned',
                condition=(Q(is_decommissioned=False) & Q(policyid__isnull=False) & Q(name__isnull=False)),
                name='%(app_label)s_%(class)s_unique_policy_name'
            ),
        )
        indexes = [
            models.Index(fields=['fortigate'])  # Create an index on the fortigate field for better performance
        ]
        verbose_name = _('policy')
        verbose_name_plural = _('policies')

    def __str__(self):
        return f'{self.fortigate} - {self.policyid}'

    def get_duplicate_name(self):
        return Policy.objects.filter(name=self.name, fortigate=self.fortigate, is_decommissioned=False).exclude(pk=self.pk)

    def get_duplicate_policyid(self):
        return Policy.objects.filter(policyid=self.policyid, fortigate=self.fortigate, is_decommissioned=False).exclude(pk=self.pk)

    def get_latest_policyid(self):
        latest_policyid = Policy.objects.filter(fortigate=self.fortigate).aggregate(Max('policyid'))['policyid__max']
        return (latest_policyid or 0) + 5

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        if not self.pk and not self.position:
            last_position = Policy.objects.filter(fortigate=self.fortigate).count()
            self.position = last_position + 1  # Assign position based on count
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        
        if not self.policyid:
            self. policyid = self.get_latest_policyid()

        if self.fortigate and self.policyid and self.get_duplicate_policyid():
            raise ValidationError('Found duplicate policy ID.')
        
        if self.profile_group and self.fortigate and self.profile_group.fortigate != self.fortigate:
            raise ValidationError({
                'profile_group': 'Profile Group must belong to the same fortigate as the policy.'
            })
        if self.schedule and self.fortigate and self.schedule.fortigate != self.fortigate:
            raise ValidationError({
                'schedule': 'Schedule must belong to the same fortigate as the policy.'
            })
        
        if self.expiry_date:
            value = self.expiry_date
            try:
                # Convert string to datetime if it's not already
                if isinstance(value, str):  
                    value = datetime.strptime(value, '%H:%M %Y/%m/%d')  
                # Make the datetime timezone-aware
                if timezone.is_naive(value):
                    value = timezone.make_aware(value, timezone.get_current_timezone())
                self.expiry_date = value
            except ValueError:
                raise ValidationError({'expiry_date': f'Invalid date format. Please use "hh:mm yyyy/mm/dd".'})
        
        # Many to Many validation
        if self.fortigate and self.pk:
            if self.source_interface.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('Source interface must belong to the same fortigate as the policy.')
            if self.destination_interface.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('Destination interface must belong to the same fortigate as the policy.')
            if self.groups.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('Group must belong to the same fortigate as the policy.')
            if self.users.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('User must belong to the same fortigate as the policy.')
            if self.source_address.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('Source address must belong to the same fortigate as the policy.')
            if self.destination_address.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('Destination address must belong to the same fortigate as the policy.')
            if self.service.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('Service must belong to the same fortigate as the policy.')
                    
        # Check for duplicate name within the same fortigate
        if self.fortigate and self.name and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})
        
    def get_status_color(self):
        return StatusChoices.colors.get(self.status)

    def get_nat_color(self):
        return NATChoices.colors.get(self.nat)
    
    def get_action_color(self):
        return ActionChoices.colors.get(self.action)


        
        
    @staticmethod
    def get_policies(fortigate, srcaddr=None, dstaddr=None, src_obj=None, dst_obj=None, port=None, protocol='TCP', user=None, date=None, start='00:00', end='00:00', all=False):
        from ..utils.policy_lookups import address_lookup, port_lookup, schedule_lookup
        """
        Retrieve policies for a given fortigate based on various filtering criteria.

        Parameters:
            fortigate (str | Fortigate): The fortigate name or Fortigate instance.
            srcaddr (str, optional): An IP address, network, or FQDN representing the source address.
            dstaddr (str, optional): An IP address, network, or FQDN representing the destination address.
            src_obj (Object, optional): An Object instance representing the source interface.
            dst_obj (Object, optional): An Object instance representing the destination interface.
            port (int | str, optional): A port (1-65535) or icmp type number (ex. 8 for ping) to filter policies by.
            protocol (str[], optional):  The protocol type, which can be 'TCP', 'UDP' or 'ICMP' (default is 'TCP').
            user (str, optional): Username for filtering policies based on user or user groups.
            all (bool, optional): If True, returns all policies for the fortigate. 
                              If False (default), returns only policies with status 'enable'.

        Returns:
            QuerySet: A filtered queryset of Policy objects ordered by position (
            lowest to highest).

        Notes:
            - If `fortigate` is a string, it is resolved to a `Fortigate` object.
            - The function only returns policies where `is_decommissioned=False`.
            - If `user` is provided, the function filters policies by matching users or groups that has the provided user.
            - Address lookups are performed using `address_lookup`, expecting `srcaddr` and `dstaddr` as lists of `Object` instances.
            - `port_lookup` is used to match policies based on the provided `port` and `protocol`.
        """
        
        objects = Policy.objects.none()
        if isinstance(fortigate, str):
            fortigate = Fortigate.objects.filter(name=fortigate).first()
            if not fortigate:
                return objects
        
        if not isinstance(fortigate, Fortigate):
            return objects

        if all:
            policies = Policy.objects.filter(fortigate=fortigate, is_decommissioned=False)
        else:
            policies = Policy.objects.filter(fortigate=fortigate, is_decommissioned=False, status='enable')

        if src_obj and isinstance(src_obj, Object):
            policies = policies.filter(source_interface__in=src_obj.intf_obj_with_any())
        if dst_obj and isinstance(dst_obj, Object):
            policies = policies.filter(destination_interface__in=dst_obj.intf_obj_with_any())
        if srcaddr:
            policies = policies.filter(source_address__in=address_lookup(fortigate, srcaddr))
        if dstaddr:
            policies = policies.filter(destination_address__in=address_lookup(fortigate, dstaddr, True))
        if port:
            policies = policies.filter(service__in=port_lookup(fortigate, port, type=protocol))
        
        # If user is provided, apply the user or group filters
        if user:
            groups = UserGroup.user_lookup(fortigate, user)
            # Filter matching user/groups or no users/groups
            policies = policies.filter(
                Q(users__in=User.objects.filter(name=user)) |
                Q(groups__in=groups) |
                Q(users__isnull=True, groups__isnull=True)
            ).distinct()

        if date:
            now = date
        else:
            now = timezone.now()
        
        # Remove expired onetime schedule
        policies = policies.filter(schedule__in=schedule_lookup(fortigate, now, start, end))
        
        # Remove expired policy
        policies = policies.filter(Q(expiry_date__gte=now) | Q(expiry='disable'))
        
        return policies.order_by('position')
    
    
    
        

class ProfileGroup(PrimaryModel):
    """
    Security Profile Group
    """
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    name = models.CharField(
        max_length=35
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
        verbose_name = _('profile group')
        verbose_name_plural = _('profile groups')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'
    
    def get_duplicate_name(self):
        return ProfileGroup.objects.exclude(pk=self.pk).filter(name=self.name, fortigate=self.fortigate, is_decommissioned=False).exists()

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        
        # Check for duplicate name within the same fortigate
        if self.fortigate and self.name and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})



class UserGroup(PrimaryModel):
    fortigate = models.ForeignKey(
        to='netbox_fortigate.Fortigate',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    name = models.CharField(
        max_length=35
    )
    '''group_type = models.CharField(
        verbose_name=_('Group Type'),
        max_length=20,
        choices=(('firewall', 'Firewall'), ('fsso-service', 'FSSO'), ('rsso', 'RSSO'), ('guest', 'Guest')),
        default='firewall',
        help_text='Set the group to be for firewall authentication, FSSO, RSSO, or guest users.'
    )'''
    member = models.ManyToManyField(
        verbose_name=_('member'),
        to='netbox_fortigate.Object',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['user', 'authentication server']},
        related_name='%(class)s_member_object',
    )
    match = models.JSONField(
        verbose_name=_('match'),
        blank=True,
        default=list,
        help_text='Group macthes.'
    )
    """member = ArrayField(
        base_field=models.CharField(max_length=64),
        verbose_name=_('member'),
        blank=True,
        default=list,
        help_text='Group member name.'
    )"""
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

        verbose_name = _('user group')
        verbose_name_plural = _('User Groups')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'
    
    def get_duplicate_name(self):
        return UserGroup.objects.filter(name=self.name, fortigate=self.fortigate, is_decommissioned=False).exclude(pk=self.pk).exists()

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        
        # Ensure members belong to the same fortigate
        if self.pk and self.member.exists() and self.member.exclude(fortigate=self.fortigate).exists():
            raise ValidationError({'member': 'All members must belong to the same fortigate.'})

        # Check for duplicate name within the same fortigate
        if self.fortigate and self.name and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})
        
    def user_lookup(fortigate, username):
        user_groups = UserGroup.objects.none()

        if isinstance(fortigate, str):
            fortigate = Fortigate.objects.filter(name=fortigate).first()
            if not fortigate:
                return user_groups

        if not isinstance(username, str):
            return user_groups

        user = User.objects.filter(fortigate=fortigate, name=username).first()
        if not user:
            return user_groups

        # Find objects related to the user and authentication server
        objs = Object.objects.filter(fortigate=fortigate, type='user', object_id=user.id)
        objs |= Object.objects.filter(fortigate=fortigate, type='authentication server', object_id=user.server.id)

        # Retrieve and return UserGroup instances
        return UserGroup.objects.filter(member__in=objs) 



        



