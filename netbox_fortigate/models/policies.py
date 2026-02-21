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
from .objects import FortiGateObject, FortiGateUser, FortiGateAuthenticationServer
from .devices import FortiGateDevice
from ipaddress import ip_address, ip_network, IPv4Address, IPv4Network


__all__ = (
    'FortiGatePolicy',
    'FortiGateProfileGroup',
    'FortiGateIPPool',
    'FortiGateUserGroup'
)


class FortiGatePolicy(PrimaryModel):
    policyid = models.PositiveBigIntegerField(
        verbose_name=_('Policy ID'),
        validators=[MinValueValidator(1), MaxValueValidator(4294967294)],
        blank=True,
        null=True,
        default=None
    )
    fortigate = models.ForeignKey(
        to='netbox_fortigate.FortiGateDevice',
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
        to='netbox_fortigate.FortiGateObject',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['zone', 'interface']},
        related_name='%(class)s_src_object',
        help_text='Incoming (ingress) interface.'
    )
    destination_interface = models.ManyToManyField(
        verbose_name=_('Destination Interface'),
        to='netbox_fortigate.FortiGateObject',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['zone', 'interface']},
        related_name='%(class)s_dst_object',
        help_text='Outgoing (egress) interface.'
    )
    action = models.CharField(
        max_length=10,
        choices=(('accept', 'Accept'), ('deny', 'Deny'), ('ipsec', 'IPsec')),
        default='accept',
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
        to='netbox_fortigate.FortiGateObject',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['address', 'address group']},
        related_name='%(class)s_srcaddr_object',
        help_text='Source IPv4 addresses and groups',
    )
    destination_address = models.ManyToManyField(
        verbose_name=_('Destination Address'),
        to='netbox_fortigate.FortiGateObject',
        limit_choices_to={'is_decommissioned': False, 'type__in': ['address', 'address group', 'Virtual IP', 'Virtual IP Group']},
        related_name='%(class)s_dstaddr_object',
        help_text='Destination IPv4 addresses and groups.',
    )
    schedule = models.ForeignKey(
        verbose_name=_('schedule'),
        to='netbox_fortigate.FortiGateObject',
        on_delete=models.PROTECT,
        limit_choices_to={'is_decommissioned': False, 'type__in': ['schedule group', 'schedule onetime', 'schedule recurring']},
        related_name='%(class)s_schedule_object',
        blank=True,
        null=True,
    )
    service = models.ManyToManyField(
        verbose_name=_('service'),
        to='netbox_fortigate.FortiGateObject',
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
        to='netbox_fortigate.FortiGateProfileGroup',
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
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='disable',
        help_text='Enable/disable source NAT.'
    )
    ip_pool = models.CharField(
        verbose_name=_('IP Pool'),
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='disable',
        help_text='Enable to use IP Pools for source NAT.'
    )
    poolname = models.ManyToManyField(
        verbose_name=_('IP Pool Name'),
        to='netbox_fortigate.FortiGateIPPool',
        limit_choices_to={'is_decommissioned': False},
        blank=True,
        related_name='%(class)s',
        help_text='IP Pool names.'
    )
    groups = models.ManyToManyField(
        verbose_name=_('groups'),
        to='netbox_fortigate.FortiGateUserGroup',
        limit_choices_to={'is_decommissioned': False},
        blank=True,
        related_name='%(class)s',
        help_text='Names of user groups that can authenticate with this policy.'
    )
    users = models.ManyToManyField(
        verbose_name=_('users'),
        to='netbox_fortigate.FortiGateUser',
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
        return FortiGatePolicy.objects.filter(name=self.name, fortigate=self.fortigate, is_decommissioned=False).exclude(pk=self.pk)

    def get_duplicate_policyid(self):
        return FortiGatePolicy.objects.filter(policyid=self.policyid, fortigate=self.fortigate, is_decommissioned=False).exclude(pk=self.pk)

    def get_latest_policyid(self):
        latest_policyid = FortiGatePolicy.objects.filter(fortigate=self.fortigate).aggregate(Max('policyid'))['policyid__max']
        return (latest_policyid or 0) + 5

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        if not self.pk and not self.position:
            last_position = FortiGatePolicy.objects.filter(fortigate=self.fortigate).count()
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
            if self.poolname.filter(~Q(fortigate=self.fortigate)).exists():
                raise ValidationError('IP Pool must belong to the same fortigate as the policy.')
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
        
        
    @staticmethod
    def get_policies(fortigate, srcaddr=None, dstaddr=None, src_obj=None, dst_obj=None, port=None, protocol='TCP', user=None, date=None, start='00:00', end='00:00', all=False):
        from ..utils.policy_lookups import address_lookup, port_lookup, schedule_lookup
        """
        Retrieve policies for a given fortigate based on various filtering criteria.

        Parameters:
            fortigate (str | FortiGateDevice): The fortigate name or FortiGateDevice instance.
            srcaddr (str, optional): An IP address, network, or FQDN representing the source address.
            dstaddr (str, optional): An IP address, network, or FQDN representing the destination address.
            src_obj (FortiGateObject, optional): An Object instance representing the source interface.
            dst_obj (FortiGateObject, optional): An Object instance representing the destination interface.
            port (int | str, optional): A port (1-65535) or icmp type number (ex. 8 for ping) to filter policies by.
            protocol (str[], optional):  The protocol type, which can be 'TCP', 'UDP' or 'ICMP' (default is 'TCP').
            user (str, optional): Username for filtering policies based on user or user groups.
            all (bool, optional): If True, returns all policies for the fortigate. 
                              If False (default), returns only policies with status 'enable'.

        Returns:
            QuerySet: A filtered queryset of Policy objects ordered by position (
            lowest to highest).

        Notes:
            - If `fortigate` is a string, it is resolved to a `FortiGateDevice` object.
            - The function only returns policies where `is_decommissioned=False`.
            - If `user` is provided, the function filters policies by matching users or groups that has the provided user.
            - Address lookups are performed using `address_lookup`, expecting `srcaddr` and `dstaddr` as lists of `Object` instances.
            - `port_lookup` is used to match policies based on the provided `port` and `protocol`.
        """
        
        objects = FortiGatePolicy.objects.none()
        if isinstance(fortigate, str):
            fortigate = FortiGateDevice.objects.filter(name=fortigate).first()
            if not fortigate:
                return objects
        
        if not isinstance(fortigate, FortiGateDevice):
            return objects

        if all:
            policies = FortiGatePolicy.objects.filter(fortigate=fortigate, is_decommissioned=False)
        else:
            policies = FortiGatePolicy.objects.filter(fortigate=fortigate, is_decommissioned=False, status='enable')

        if src_obj and isinstance(src_obj, FortiGateObject):
            policies = policies.filter(source_interface__in=src_obj.intf_obj_with_any())
        if dst_obj and isinstance(dst_obj, FortiGateObject):
            policies = policies.filter(destination_interface__in=dst_obj.intf_obj_with_any())
        if srcaddr:
            policies = policies.filter(source_address__in=address_lookup(fortigate, srcaddr))
        if dstaddr:
            policies = policies.filter(destination_address__in=address_lookup(fortigate, dstaddr, True))
        if port:
            policies = policies.filter(service__in=port_lookup(fortigate, port, type=protocol))
        
        # If user is provided, apply the user or group filters
        if user:
            groups = FortiGateUserGroup.user_lookup(fortigate, user)
            # Filter matching user/groups or no users/groups
            policies = policies.filter(
                Q(users__in=FortiGateUser.objects.filter(name=user)) |
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
    
    
    
        

class FortiGateProfileGroup(PrimaryModel):
    """
    Security Profile Group
    """
    fortigate = models.ForeignKey(
        to='netbox_fortigate.FortiGateDevice',
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
        return FortiGateProfileGroup.objects.exclude(pk=self.pk).filter(name=self.name, fortigate=self.fortigate, is_decommissioned=False).exists()

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        
        # Check for duplicate name within the same fortigate
        if self.fortigate and self.name and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class FortiGateIPPool(PrimaryModel):
    fortigate = models.ForeignKey(
        to='netbox_fortigate.FortiGateDevice',
        on_delete=models.CASCADE,
        related_name='%(class)s',
        limit_choices_to={'role__in': SUPPORTED_POLICY_DEVICE_ROLE},
    )
    name = models.CharField(
        max_length=35
    )
    type = models.CharField(
        verbose_name=_('type'),
        max_length=22,
        choices=IPPoolTypeChoices,
        default=IPPoolTypeChoices.DEFAULT,
        help_text='IP pool type: overload, one-to-one, fixed-port-range, port-block-allocation.'
    )
    startip = HostAddressField(
        verbose_name=_('Start IP'),
        default='0.0.0.0',
        help_text=_('First IPv4 address (inclusive) in the range for the address pool (format xxx.xxx.xxx.xxx, Default: 0.0.0.0).')
    )
    endip = HostAddressField(
        verbose_name=_('End IP'),
        default='0.0.0.0',
        help_text=_('Final IPv4 address (inclusive) in the range for the address pool (format xxx.xxx.xxx.xxx, Default: 0.0.0.0).')
    )
    startport = models.PositiveIntegerField(
        verbose_name=_('Start Port'),
        validators=[MinValueValidator(1024), MaxValueValidator(65535)],
        default=5117,
        help_text='First port number (inclusive) in the range for the address pool (1024 - 65535, Default: 5117).'
    )
    endport = models.PositiveIntegerField(
        verbose_name=_('End Port'),
        validators=[MinValueValidator(1024), MaxValueValidator(65535)],
        default=65533,
        help_text='Final port number (inclusive) in the range for the address pool (1024 - 65535, Default: 65533).'
    )
    source_startip = HostAddressField(
        verbose_name=_('Source Start IP'),
        default='0.0.0.0',
        help_text=_('First IPv4 address (inclusive) in the range of the source addresses to be translated (format = xxx.xxx.xxx.xxx, default = 0.0.0.0).')
    )
    source_endip = HostAddressField(
        verbose_name=_('Source End IP'),
        default='0.0.0.0',
        help_text=_('Final IPv4 address (inclusive) in the range of the source addresses to be translated (format xxx.xxx.xxx.xxx, Default: 0.0.0.0).')
    )
    block_size = models.PositiveSmallIntegerField(
        verbose_name=_('Block Size'),
        validators=[MinValueValidator(64), MaxValueValidator(4096)],
        default=128,
        help_text=_('Number of addresses in a block (64 - 4096, default = 128).')
    )
    num_blocks_per_user = models.PositiveSmallIntegerField(
        verbose_name=_('Port Per User'),
        validators=[MinValueValidator(1), MaxValueValidator(128)],
        default=8,
        help_text=_('Number of addresses blocks that can be used by a user (1 to 128, default = 8).')
    )
    arp_reply = models.CharField(
        verbose_name=_('ARP Reply'),
        max_length=7,
        choices=(('enable', 'Enable'), ('disable', 'Disable')),
        default='enable',
        help_text=_('Enable/disable replying to ARP requests when an IP Pool is added to a policy (default = enable).')
    )
    comments = models.TextField(
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
        verbose_name = _('IP Pool')
        verbose_name_plural = _('IP Pools')

    def __str__(self):
        return f'{self.fortigate} - {self.name}'
    
    def get_duplicate_name(self):
        return FortiGateIPPool.objects.filter(name=self.name, fortigate=self.fortigate, is_decommissioned=False).exclude(pk=self.pk).exists()

    # Ensure validation is check when creating or updating object in shell or form
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        
        # Ensure Start IP is not greater than End IP
        if ip_address(self.startip) > ip_address(self.endip):
            raise ValidationError({'startip': 'Start IP cannot be greater than End IP.'})

        # Ensure Source Start IP is not greater than Source End IP
        if ip_address(self.source_startip) > ip_address(self.source_endip):
            raise ValidationError({'source_startip': 'Source Start-IP cannot be greater than Source End-IP.'})

        # Ensure Start Port is not greater than End Port
        if self.startport > self.endport:
            raise ValidationError({'startport': 'Start Port cannot be greater than End Port.'})

        # Check for duplicate name within the same fortigate
        if self.fortigate and self.name and self.get_duplicate_name():
            raise ValidationError({'name': 'Found duplicate name.'})


class FortiGateUserGroup(PrimaryModel):
    fortigate = models.ForeignKey(
        to='netbox_fortigate.FortiGateDevice',
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
        to='netbox_fortigate.FortiGateObject',
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
        return FortiGateUserGroup.objects.filter(name=self.name, fortigate=self.fortigate, is_decommissioned=False).exclude(pk=self.pk).exists()

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
        user_groups = FortiGateUserGroup.objects.none()

        if isinstance(fortigate, str):
            fortigate = FortiGateDevice.objects.filter(name=fortigate).first()
            if not fortigate:
                return user_groups

        if not isinstance(username, str):
            return user_groups

        user = FortiGateUser.objects.filter(fortigate=fortigate, name=username).first()
        if not user:
            return user_groups

        # Find objects related to the user and authentication server
        objs = FortiGateObject.objects.filter(fortigate=fortigate, type='user', object_id=user.id)
        objs |= FortiGateObject.objects.filter(fortigate=fortigate, type='authentication server', object_id=user.server.id)

        # Retrieve and return UserGroup instances
        return FortiGateUserGroup.objects.filter(member__in=objs) 



        



