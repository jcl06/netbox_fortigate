from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse

from netbox.models import PrimaryModel, JobsMixin
from ipam.fields import IPAddressField, IPNetworkField
from netbox_fortigate.utils.settings import get_plugin_default
from django.core.validators import RegexValidator

__all__ = (
    "FortiGateDevice",
    "FortiGateInterface",
    "FortiGateRoute",
    "FortiGateZone",
    "default_api_port",
    "default_ssh_port",
    # "FortiGateObject"
)



fortios_version_validator = RegexValidator(
    regex=r"^v\d+\.\d+(?:\.\d+)?$",
    message=_("Enter a FortiOS version like v7.2 or v7.2.3."),
)

def default_api_port():
    return get_plugin_default("default_api_port", 443) or 443


def default_ssh_port():
    return get_plugin_default("default_ssh_port", 22) or 22


class FortiGateDevice(PrimaryModel, JobsMixin):
    device = models.OneToOneField(
        to='dcim.Device',
        on_delete=models.PROTECT,
        related_name="fortigate",
    )

    enabled = models.BooleanField(default=True)

    role = models.CharField(
        max_length=64,
        default="firewall",
        help_text=_("FortiGate plugin role key (e.g. user_vpn). Defaults from linked Device.role on creation."),
    )

    mgmt_ip = models.ForeignKey(
        verbose_name=_("Management IP"),
        to='ipam.IPAddress',
        on_delete=models.SET_NULL,      
        related_name="+",
        blank=True,
        null=True,
        help_text=_("NetBox IPAddress object used to reach this FortiGate (override)."),
    )

    priority = models.PositiveSmallIntegerField(default=1)
    default_vdom = models.CharField(verbose_name=_("Default VDOM"), max_length=64, default="root")
    api_port = models.PositiveIntegerField(verbose_name=_("API Port"), default=default_api_port)
    ssh_port = models.PositiveIntegerField(verbose_name=_("SSH Port"), default=default_ssh_port)
    fortios_version = models.CharField(
        verbose_name=_("FortiOS Version"),
        max_length=32,
        validators=[fortios_version_validator],
        help_text=_("Format: v7.2 or v7.2.3"),
    )

    class Meta:
        ordering = ("device__name",)
        verbose_name = _("Firewall")
        verbose_name_plural = _("Firewalls")

    def __str__(self) -> str:
        return self.device.name
    
    def save(self, *args, **kwargs):
        # Only set a default role at creation time if empty
        if not self.pk and not self.role and self.device_id:
            # Prefer slug-like value; fallback to name if slug missing
            if getattr(self.device, "role_id", None) and self.device.role:
                self.role = getattr(self.device.role, "slug", "") or getattr(self.device.role, "name", "") or ""
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # If Device has no primary IP, mgmt_ip becomes required
        if self.device_id:
            has_primary = bool(getattr(self.device, "primary_ip4_id", None) or getattr(self.device, "primary_ip6_id", None))
            if not has_primary and not self.mgmt_ip_id:
                raise ValidationError(
                    {"mgmt_ip": _("Management IP is required when the Device has no primary IP.")}
                )
            
        if self.mgmt_ip_id and self.device_id:
            ao = getattr(self.mgmt_ip, "assigned_object", None)
            ip_device = getattr(ao, "device", None)
            if ip_device and ip_device.pk != self.device_id:
                raise ValidationError({"mgmt_ip": _("Selected IP is assigned to a different device.")})

    
    
    @property
    def ip_address(self):
        if self.mgmt_ip:
            ip = self.mgmt_ip.address
            return str(getattr(ip, "ip", ip)) 
        if getattr(self.device, "primary_ip4", None):
            ip = self.device.primary_ip4.address  # depending on NetBox object
            return str(getattr(ip, "ip", ip)) 
        if getattr(self.device, "primary_ip6", None):
            ip = self.device.primary_ip6.address
            return str(getattr(ip, "ip", ip)) 
        return None

    # def get_absolute_url(self):
    #     return reverse('netbox_fortigate:fortigatedevice', args=[self.pk])


class FortiGateInterface(PrimaryModel):
    fortigate = models.ForeignKey(
        to=FortiGateDevice,
        on_delete=models.PROTECT,
        related_name="interfaces",
    )
    name = models.CharField(max_length=64)

    enabled = models.BooleanField(default=True)

    ip = IPAddressField(
        verbose_name=_("IP Address"),
        blank=True,
        null=True,
        help_text=_("IPv4 or IPv6 address (with prefix length)"),
    )

    type = models.CharField(max_length=15, blank=True)

    role = models.CharField(
        max_length=32,
        choices=(
            ("", "-"),
            ("lan", "LAN"),
            ("wan", "WAN"),
            ("dmz", "DMZ"),
            ("undefined", "Undefined"),
        ),
        blank=True,
        default="",
    )

    parent = models.ForeignKey(
        to="self",
        on_delete=models.RESTRICT,
        related_name="child_interfaces",
        null=True,
        blank=True,
        verbose_name=_("parent interface"),
    )

    vdom = models.CharField(
        verbose_name=_("VDOM"),
        max_length=64,
        default="root",
    )

    status = models.CharField(
        max_length=8,
        choices=(("up", "Up"), ("down", "Down")),
        default="down",
        help_text=_("Interface status"),
    )

    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("fortigate", "name"), name="uniq_fg_if_name"),
        ]
        ordering = ("fortigate__device__name", "name")
        verbose_name = _("Firewall Interface")
        verbose_name_plural = _("Firewall Interfaces")

    @property
    def parent_object(self):
        return self.fortigate

    @property
    def members(self):
        # Native because of related_name="child_interfaces"
        return self.child_interfaces.all()

    @property
    def zone(self):
        # This M2M is defined on FortiGateZone.interface with related_name="zones"
        return self.zones.first()

    @property
    def device(self):
        return self.fortigate.device

    def __str__(self):
        return f"{self.device} - {self.name}"

    def clean(self):
        super().clean()

        if not self.fortigate_id:
            raise ValidationError({"fortigate": _("FortiGate device is required.")})

        # /0 masks are not acceptable
        if self.ip and getattr(self.ip, "prefixlen", None) == 0:
            raise ValidationError({"ip": _("Cannot create IP address with /0 mask.")})

        # Duplicate IP (only enforce when enabled and IP set; scoped to the same FortiGateDevice)
        if self.enabled and self.ip:
            if FortiGateInterface.objects.filter(
                fortigate_id=self.fortigate_id,
                enabled=True,
                ip=self.ip,
            ).exclude(pk=self.pk).exists():
                raise ValidationError({"ip": _("Duplicate IP address found on this FortiGate.")})

        # Optional: prevent interface name clashing with a zone name on same FortiGate
        if self.name and FortiGateZone.objects.filter(
            fortigate_id=self.fortigate_id,
            name=self.name,
        ).exclude(pk=getattr(self, "pk", None)).exists():
            raise ValidationError({"name": _("Interface name conflicts with an existing zone name.")})



class FortiGateZone(PrimaryModel):
    name = models.CharField(max_length=35)

    fortigate = models.ForeignKey(
        to=FortiGateDevice,
        on_delete=models.PROTECT,
        related_name="zones",
    )

    type = models.CharField(
        max_length=16,
        default="normal",
        choices=(("normal", "Normal"), ("sdwan", "SDWAN")),
    )

    intrazone = models.CharField(
        verbose_name=_("intra-zone"),
        max_length=8,
        default="deny",
        choices=(("allow", "Allow"), ("deny", "Deny")),
    )

    interface = models.ManyToManyField(
        to=FortiGateInterface,
        related_name="zones",
        blank=True,
    )

    is_decommissioned = models.BooleanField(verbose_name=_("decommissioned"), default=False)

    class Meta:
        ordering = ("fortigate__device__name", "name")
        constraints = [
            models.UniqueConstraint(fields=("fortigate", "name"), name="uniq_fg_zone_name"),
        ]
        verbose_name = _("Firewall Zone")
        verbose_name_plural = _("Firewall Zones")

    def __str__(self):
        return f"{self.fortigate.device} - {self.name}"

    def clean(self):
        super().clean()

        if not self.fortigate_id:
            raise ValidationError({"fortigate": _("FortiGate device is required.")})

        # Zone name must be unique for this FortiGate
        if self.name and FortiGateZone.objects.filter(
            fortigate_id=self.fortigate_id,
            name=self.name,
        ).exclude(pk=self.pk).exists():
            raise ValidationError({"name": _("Found duplicate zone name.")})

        # Prevent zone name clashing with an interface name on same FortiGate
        if self.name and FortiGateInterface.objects.filter(
            fortigate_id=self.fortigate_id,
            name=self.name,
        ).exclude(pk=None).exists():
            raise ValidationError({"name": _("Zone name conflicts with an existing interface name.")})



class FortiGateRoute(PrimaryModel):
    route = IPNetworkField(
        verbose_name=_("Route"),
        help_text=_("IPv4/IPv6 network with mask (CIDR)"),
    )

    version = models.SmallIntegerField(
        choices=((4, "IPv4"), (6, "IPv6")),
        default=4,
    )

    fortigate = models.ForeignKey(
        verbose_name=_("FortiGate"),
        to=FortiGateDevice,
        on_delete=models.PROTECT,
        related_name="routes",
    )

    type = models.CharField(
        max_length=64,
        default="connect",
        help_text=_("Route type (e.g. connect/static/ospf/bgp)"),
    )

    gateway = IPAddressField(
        verbose_name=_("Gateway"),
        blank=True,
        null=True,
        help_text=_("IPv4 or IPv6 address (no prefix length)"),
    )

    next_hop = models.ForeignKey(
        verbose_name=_("Next hop"),
        to=FortiGateDevice,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="next_hop_routes",
    )

    interface = models.ForeignKey(
        to=FortiGateInterface,
        on_delete=models.PROTECT,
        related_name="routes",
    )

    distance = models.SmallIntegerField(verbose_name=_("AD"), default=0)
    priority = models.SmallIntegerField(default=0)
    metric = models.SmallIntegerField(default=0)

    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("-route", "distance", "metric")
        constraints = [
            models.UniqueConstraint(
                fields=("fortigate", "route", "interface", "enabled"),
                name="uniq_fg_route_per_interface_enabled",
            ),
            models.UniqueConstraint(
                fields=("fortigate", "route", "interface", "gateway", "enabled"),
                name="uniq_fg_route_gateway_per_interface_enabled",
            ),
        ]
        verbose_name = _("routing table")
        verbose_name_plural = _("routing table")

    @property
    def device(self):
        return self.fortigate.device

    def __str__(self):
        return f"{self.device} - {self.route}"

    def clean(self):
        super().clean()

        if not self.fortigate_id:
            raise ValidationError({"fortigate": _("FortiGate is required.")})

        # Ensure interface belongs to the same FortiGate
        if self.interface_id and self.interface.fortigate_id != self.fortigate_id:
            raise ValidationError({"interface": _("Interface must belong to the same FortiGate.")})

        # Enforce gateway family matches version (basic sanity)
        if self.gateway:
            gw_family = getattr(self.gateway, "version", None)  # IPAddressField returns ipaddress obj-like
            if self.version == 4 and gw_family != 4:
                raise ValidationError({"gateway": _("Gateway must be IPv4 for version 4 routes.")})
            if self.version == 6 and gw_family != 6:
                raise ValidationError({"gateway": _("Gateway must be IPv6 for version 6 routes.")})

        # Auto-derive next_hop if gateway matches exactly one FortiGateInterface IP in our plugin cache
        if self.gateway:
            matches = FortiGateInterface.objects.filter(
                enabled=True,
                ip__net_host=str(self.gateway),
            )
            if matches.count() == 1:
                self.next_hop = matches.first().fortigate
            elif matches.count() > 1:
                # Don’t hard fail; leave next_hop unset and let UI show ambiguity later
                self.next_hop = None

    def validate_unique(self, *args, **kwargs):
        super().validate_unique(*args, **kwargs)

        # Legacy behavior: for connected routes, route must be unique (per FortiGate) among connect routes
        if self.enabled and self.type == "connect":
            q = FortiGateRoute.objects.filter(
                fortigate_id=self.fortigate_id,
                route=self.route,
                type="connect",
                enabled=True,
            ).exclude(pk=self.pk)
            if q.exists():
                raise ValidationError(_("%(route)s conflicts with existing connected route (ID %(id)s).") % {
                    "route": self.route,
                    "id": q.first().pk,
                })

    @property
    def next_hop_interface(self):
        if not self.gateway:
            return None
        matches = FortiGateInterface.objects.filter(
            enabled=True,
            ip__net_host=str(self.gateway),
        )
        if matches.count() == 1:
            return matches.first()
        return None
    
