import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import mark_safe

from netbox.tables import NetBoxTable, columns
from ..models import *

from ..utils.policy_lookups import get_objects_values

__all__ = (
    'PolicyTable',
)


class PolicyTable(NetBoxTable):
    policyid = tables.Column(
        linkify=True,
    )
    fortigate = tables.Column(
        linkify=True,
        verbose_name=_('Fortigate'),
        attrs={'td': {'class': 'text-nowrap'}}
    )
    source_interface = tables.Column(
        verbose_name=_('Source Interface'),
    )
    destination_interface = tables.Column(
        verbose_name=_('Destination Interface'),
    )
    actions = columns.ActionsColumn(
        actions=('delete',) 
    )

    class Meta(NetBoxTable.Meta):
        model = Policy
        fields = (
            'pk', 'id', 'is_decommissioned', 'name', 'fortigate', 'comments', 'tags',  'action', 'status',
            'policyid', 'source_interface', 'destination_interface', 'source_address', 'destination_address',
            'schedule', 'service', 'inspection_mode', 'security_profile', 'logging', 'nat', 'expiry_date', 
            'users'

        )
        default_columns = (
            'pk', 'policyid', 'fortigate', 'source_interface', 'destination_interface', 'source_address',
            'destination_address', 'service', 'action', 'schedule', 
        )

    def render_source_interface(self, value, record):
        urls = []
        for member in value.all():
            urls.append(format_html(f'<a href="{member.object.get_absolute_url()}">{member.object}</a>'))

        return format_html(', '.join(urls))
    
    def render_destination_interface(self, value, record):
        urls = []
        for member in value.all():
            urls.append(format_html(f'<a href="{member.object.get_absolute_url()}">{member.object}</a>'))

        return format_html(', '.join(urls))


    def render_source_address(self, value, record):
        return get_objects_values(value.all(), True)
    
    def render_destination_address(self, value, record):
        return get_objects_values(value.all(), True)
    
    def render_service(self, value, record):
        return get_objects_values(value.all(), True)
    
    def render_schedule(self, value, record):
        return get_objects_values([value], True)
    
    def render_users(self, value, record):
        users = []
        if record.users.all():
            users.extend(get_objects_values(record.users.all(), False, "User"))
        if record.groups.all():
            users.extend(get_objects_values(record.groups.all(), False, "UserGroup"))
        return ", ".join(users)

