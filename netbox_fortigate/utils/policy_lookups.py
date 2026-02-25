import logging
import re
from datetime import datetime

from django.db.models import Q, F, Func, Value, ExpressionWrapper, Case, When, BooleanField
from django.db.models.fields import GenericIPAddressField
from django.utils import timezone

from ..models import *
from .find_policy import find_policy
from ipaddress import ip_address, ip_network
from .misc import *
from .inventory import update_inventory

logger = logging.getLogger(__name__)

__all__ = (
    'is_connection_allowed',
    'address_lookup',
    'port_lookup',
    'schedule_lookup',
    'get_objects_values'
)

def is_connection_allowed(src, dst, protocol=1, port=0, auth_type=None, user_group=None, icmptype=None, count=0):
    """
    Find if communication from source to destination is allowed
    :param src:
    :param dst:
    :return:
    """
    output = [False, 'Unknown']
    try:
        status = find_path(src, dst)
        if not status[0]:
            raise Exception(status[1])
        path = status[1]
        results = {}
        for device, item in path.items():
            policies = {
                'allow': [],
                'deny': []
            }
            allowed = 'unknown'
            policy_count = 0
            interface_with_no_policy = []
            source_interface = []

            # To verify if source interface is the same with exit interface to reach the source.
            status = find_route(src, device=device)
            if not status[0]:
                raise Exception(status[1])
            tmp_srcintf = []
            for route in status[1]:
                if route.interface.parent and route.interface.parent in item['src']:
                    tmp_srcintf.append(route.interface)
            if tmp_srcintf:
                item['src'] = tmp_srcintf

            for srcintf in item['src']:
                source_interface.append(srcintf)
                #  To remove auth_type and user_group for firewall not using user on the policy rules
                if auth_type and user_group and device.role != 'user_vpn':
                    auth_type = user_group = None
                
                status = find_policy(device, srcintf.name, src, dst, protocol, port, auth_type, user_group, icmptype)
                if status[0]:
                    if status[1] > 0:  # Referred to Policy ID, 0 means no policy matched
                        policy_count += 1
                        if status[2] == 'accept':
                            if status[1] not in policies['allow']:
                                policies['allow'].append(status[1])
                            allowed = 'allow'
                        if status[2] == 'deny':
                            if status[1] not in policies['deny']:
                                policies['deny'].append(status[1])
                            allowed = 'deny'
                    else:
                        interface_with_no_policy.append(srcintf)
                else:
                    logger.warning(status[1])
                    policy_count = len(item['src'])
            if policy_count != len(item['src']):  # To check if has policy for all source interfaces
                allowed = 'deny'
            if allowed in ['unknown', 'deny']:
                if allowed in ['unknown', 'deny'] and count == 3:
                    update_inventory(device, True)
                src_obj = get_interface_object(device, item['src'])
                dst_obj = get_interface_object(device, item['dst'])
                if src_obj and dst_obj:
                    if icmptype and protocol.upper() == 'ICMP':
                        port = icmptype
                    # print(f'checking: {device}, {src}, {dst}, {src_obj}, {dst_obj}, {port}, {protocol}, {user_group}')
                    logger.info('Looking in Policy table')
                    policies = Policy.get_policies(device, src, dst, src_obj, dst_obj, port, protocol, user_group, date=timezone.now())
                    if policies:
                        allowed = policies.first().action
                        if allowed == 'accept':
                            allowed = 'allow'
                            policies = {'allow': [policies.first().policyid], 'deny': []}
                        else:
                            allowed = 'deny'
                            policies = {'deny': [policies.first().policyid], 'allow': []}
                    else:
                        allowed = 'deny'
                        policies = {'allow': [], 'deny': [0]}
            results[device] = {
                # 'device': device,
                'status': allowed,
                'policies': policies,
                'source_interface': source_interface,
                'interface_has_no_policy': interface_with_no_policy,
            }
        output = [True, results, path]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output


class INET(Func):
    function = 'INET'
    output_field = GenericIPAddressField()

def get_vips_by_ip(device, address):
    """Returns VIPs based on the device and IP address or range."""
    # Annotate VIP entries with range logic
    vip_addresses = VIP.objects.filter(fortigate=device).annotate(
        is_range=Case(
            When(external_ip__contains='-', then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        start_ip=ExpressionWrapper(
            Case(
                When(is_range=True, then=Func(F('external_ip'), Value('-'), Value(1), function='split_part')),
                default=F('external_ip'),
                output_field=GenericIPAddressField()
            ),
            output_field=GenericIPAddressField()
        ),
        end_ip=ExpressionWrapper(
            Case(
                When(is_range=True, then=Func(F('external_ip'), Value('-'), Value(2), function='split_part')),
                default=F('external_ip'),
                output_field=GenericIPAddressField()
            ),
            output_field=GenericIPAddressField()
        ),
        ip_value=ExpressionWrapper(INET(Value(address)), output_field=GenericIPAddressField())
    ).filter(
        Q(external_ip=address) |  # Exact match
        (
            Q(is_range=True) &  # Only apply the range logic if it is a range
            Q(ip_value__gte=F('start_ip')) & 
            Q(ip_value__lte=F('end_ip'))
        )
    )
    
    return vip_addresses


def address_lookup(device, address, dstaddr=False):
    objects = set()
    addresses = set()
    address = address.lower()
    address_type = is_network_or_ip(address)

    if isinstance(device, str):
        device = Fortigate.objects.filter(name=device).first()
        if not device:
            return objects

    # Handle IP Address or Network
    if address_type == "IP Address":
        addresses.update(Address.objects.filter(
            fortigate=device, type='iprange', start_ip__lte=address, end_ip__gte=address
        ).values_list('id', flat=True))
        addresses.update(Address.objects.filter(
            fortigate=device, subnet__net_contains_or_equals =address
        ).values_list('id', flat=True))
    
    if address_type == "Network":
        addresses.update(Address.objects.filter(
            fortigate=device, subnet__net_contains_or_equals =address
        ).values_list('id', flat=True))
    
    # Handle FQDN and Subdomains
    else:
        domain = ".".join(address.split(".")[-2:])
        addresses.update(Address.objects.filter(fortigate=device, type='fqdn').filter(
            Q(fqdn__iexact=domain) |  # Exact match
            Q(fqdn__iexact=f'*.{domain}') |  # Match *.abc.com
            Q(fqdn__iendswith=f'.{domain}')  # Match subdomains like 123.abc.com
        ).values_list('id', flat=True))
        addresses.update(Address.objects.filter(fortigate=device, subnet='0.0.0.0/0').values_list('id', flat=True))

    # Retrieve address objects and groups
    address_objs = Object.objects.filter(type='address', object_id__in=addresses)
    address_group = AddressGroup.objects.filter(member__in=address_objs)
    address_group_objs = Object.objects.filter(fortigate=device, type='address group', object_id__in=address_group)
    objects.update(address_objs)
    objects.update(address_group_objs)

    if dstaddr:
        vip_addresses = set()
        if address_type == "Invalid Address":
            domain = ".".join(address.split(".")[-2:])
            vip_addresses = VIP.objects.filter(fortigate=device).filter(
                Q(external_address__fqdn__iexact=domain) |  # Exact match
                Q(external_address__fqdn__iexact=f'*.{domain}') |  # Match *.abc.com
                Q(external_address__fqdn__iendswith=f'.{domain}')  # Match subdomains like 123.abc.com
            )
        elif address_type == 'IP Address':
            vip_addresses = get_vips_by_ip(device, address)  # VIP filter based on IP range
        vip_objs = Object.objects.filter(type='Virtual IP', object_id__in=vip_addresses.values_list('id', flat=True))
        vip_group = VIPGroup.objects.filter(member__in=vip_addresses)
        vip_group_objs = Object.objects.filter(fortigate=device, type='Virtual IP Group', object_id__in=vip_group)
        objects.update(vip_objs)
        objects.update(vip_group_objs)

    return objects


def is_network_or_ip(addr):
    """Check if the provided address is an IP address or network."""
    try:
        ip_address(addr)  # This will raise ValueError if addr is not a valid IP address
        return "IP Address"
    except ValueError:
        pass  # Not an IP address, continue to check if it's a network

    try:
        ip_network(addr)  # This will raise ValueError if addr is not a valid network
        return "Network"
    except ValueError:
        return "Invalid Address"


def get_vips_by_ip(device, address):
    """Returns VIPs based on the device and IP address or range."""
    # Annotate VIP entries with range logic
    vip_addresses = VIP.objects.filter(fortigate=device).annotate(
        is_range=Case(
            When(external_ip__contains='-', then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        start_ip=ExpressionWrapper(
            Case(
                When(is_range=True, then=Func(F('external_ip'), Value('-'), Value(1), function='split_part')),
                default=F('external_ip'),
                output_field=GenericIPAddressField()
            ),
            output_field=GenericIPAddressField()
        ),
        end_ip=ExpressionWrapper(
            Case(
                When(is_range=True, then=Func(F('external_ip'), Value('-'), Value(2), function='split_part')),
                default=F('external_ip'),
                output_field=GenericIPAddressField()
            ),
            output_field=GenericIPAddressField()
        ),
        ip_value=ExpressionWrapper(INET(Value(address)), output_field=GenericIPAddressField())
    ).filter(
        Q(external_ip=address) |  # Exact match
        (
            Q(is_range=True) &  # Only apply the range logic if it is a range
            Q(ip_value__gte=F('start_ip')) & 
            Q(ip_value__lte=F('end_ip'))
        )
    )
    
    return vip_addresses


def address_lookup(device, address, dstaddr=False):
    objects = Object.objects.none()
    addresses = set()
    address = address.lower()
    address_type = is_network_or_ip(address)

    if isinstance(device, str):
        device = Fortigate.objects.filter(fortigate=device).first()
        if not device:
            return objects

    # Handle IP Address
    if address_type == "IP Address":
        addresses.update(Address.objects.filter(
            fortigate=device, type='iprange', start_ip__lte=address, end_ip__gte=address
        ).values_list('id', flat=True))
        addresses.update(Address.objects.filter(
            fortigate=device, subnet__net_contains_or_equals =address
        ).values_list('id', flat=True))

    # Handle Network Address
    elif address_type == "Network":
        addresses.update(Address.objects.filter(
            fortigate=device, subnet__net_contains_or_equals =address
        ).values_list('id', flat=True))
    
    # Handle FQDN and Subdomains
    elif address_type == "FQDN":
        domain = ".".join(address.split(".")[-2:])
        addresses.update(Address.objects.filter(fortigate=device, type='fqdn').filter(
            Q(fqdn__iexact=domain) |  # Exact match
            Q(fqdn__iexact=f'*.{domain}') |  # Match *.abc.com
            Q(fqdn__iendswith=f'.{domain}')  # Match subdomains like 123.abc.com
        ).values_list('id', flat=True))
        addresses.update(Address.objects.filter(fortigate=device, subnet='0.0.0.0/0').values_list('id', flat=True))
    else:
        logger.info(f'{address} is not a valid address.')
        return objects
    
    # Retrieve address objects and groups
    objects = Object.objects.filter(fortigate=device, type='address', object_id__in=addresses)
    address_group = AddressGroup.objects.filter(member__in=objects)
    address_group_objs = Object.objects.filter(fortigate=device, type='address group', object_id__in=address_group)
    objects |= address_group_objs

    if dstaddr:
        vip_addresses = set()
        if address_type == "FQDN":
            domain = ".".join(address.split(".")[-2:])
            vip_addresses = VIP.objects.filter(fortigate=device).filter(
                Q(external_address__fqdn__iexact=domain) |  # Exact match
                Q(external_address__fqdn__iexact=f'*.{domain}') |  # Match *.abc.com
                Q(external_address__fqdn__iendswith=f'.{domain}')  # Match subdomains like 123.abc.com
            )
        elif address_type == 'IP Address':
            vip_addresses = get_vips_by_ip(device, address)  # VIP filter based on IP range
        vip_objs = Object.objects.filter(fortigate=device, type='Virtual IP', object_id__in=vip_addresses.values_list('id', flat=True))
        objects |= vip_objs
        vip_group = VIPGroup.objects.filter(member__in=vip_addresses)
        vip_group_objs = Object.objects.filter(fortigate=device, type='Virtual IP Group', object_id__in=vip_group)
        objects |= vip_group_objs

    return objects


def is_network_or_ip(addr):
    """Check if the provided address is an IP address or network."""
    try:
        ip_address(addr)  # This will raise ValueError if addr is not a valid IP address
        return "IP Address"
    except ValueError:
        pass  # Not an IP address, continue to check if it's a network

    try:
        ip_network(addr)  # This will raise ValueError if addr is not a valid network
        return "Network"
    except ValueError:
        if is_valid_fqdn:
            return 'FQDN'
        return "Invalid Address"


def is_valid_fqdn(domain):
    fqdn_regex = re.compile(
        r"^(?!-)([a-zA-Z0-9-_]{1,63}\.)+[a-zA-Z]{2,63}$"
    )
    return bool(fqdn_regex.match(domain))


def port_lookup(device, port, type='TCP'):
    objects = Object.objects.none()
    type = type.upper()

    if isinstance(device, str):
        device = Fortigate.objects.filter(name=device).first()
        if not device:
            return objects
            
    if isinstance(port, str):  # Check if port is a string
        try:
            port = int(port) 
        except ValueError:
            return objects 
    
    if not isinstance(port, int):  # Ensure port is an integer
        return objects
    
    # Get the list of service IDs based on type (tcp/udp)
    if type == 'TCP':
        services = list(Services.objects.filter(fortigate=device, tcp_portrange=port).values_list('id', flat=True))
    elif type == 'UDP':
        services = list(Services.objects.filter(fortigate=device, udp_portrange=port).values_list('id', flat=True))
    elif type == 'ICMP':
        services = list(Services.objects.filter(fortigate=device).filter(
            Q(protocol='ICMP', icmptype__isnull=True) | 
            Q(protocol='IP', protocol_number=0)
        ).values_list('id', flat=True))
        services.extend(Services.objects.filter(fortigate=device, protocol='ICMP', icmptype=port).values_list('id', flat=True))
    else: 
        return objects
    
    # Retrieve service objects based on service IDs
    objects = Object.objects.filter(type='service', object_id__in=services)

    # Retrieve service group objects based on members of the above service objects
    service_group = ServiceGroup.objects.filter(member__in=objects)
    service_group_objs = Object.objects.filter(fortigate=device, type='service group', object_id__in=service_group)

    # Combine the service group objects with the service objects using union
    objects |= service_group_objs
    
    return objects


def schedule_lookup(device, date=timezone.now(), start='00:00', end='00:00'):
    objects = Object.objects.none()
    schedule_objs = set()

    if isinstance(device, str):
        device = Fortigate.objects.filter(name=device).first()
        if not device:
            return objects

    if all(isinstance(val, str) for val in [start, end]):
        try:
           start = datetime.strptime(start, '%H:%M').time()
           end = datetime.strptime(end, '%H:%M').time()
        except ValueError:
            return objects
    else:
        return objects
    
    if not isinstance(date, datetime):
        return objects
    
    today = date.strftime('%A').lower()
    onetime_schedules = ScheduleOnetime.objects.filter(fortigate=device, start__lte=date, end__gte=date).values_list('id', flat=True)
    onetime_schedules_objs = Object.objects.filter(fortigate=device, type='schedule onetime', object_id__in=onetime_schedules)
    schedule_objs.update(onetime_schedules_objs)
    objects = onetime_schedules_objs
    
    recurring_schedules = ScheduleRecurring.objects.filter(
        fortigate=device, day__icontains=today, start__lte=start, end__gte=end).values_list('id', flat=True)
    recurring_schedules_objs = Object.objects.filter(fortigate=device, type='schedule recurring', object_id__in=recurring_schedules)
    schedule_objs.update(recurring_schedules_objs)
    objects |= recurring_schedules_objs
    
    schedule_group = ScheduleGroup.objects.filter(member__in=schedule_objs)
    schedule_group_objs = Object.objects.filter(fortigate=device, type='schedule group', object_id__in=schedule_group)
    objects |= schedule_group_objs

    return objects


def policy_lookup(device, src, dst, src_obj, dst_obj, port=None, protocol='TCP', user=None):
    from ..models import Policy
    output = [False, 'Unknown']
    allowed = 'deny'
    try:
        if isinstance(device, str):
            device = Fortigate.objects.filter(name=device).first()
            if not device:
                raise Exception(f'{device} does not exist')

        if not all(isinstance(obj, Object) for obj in (src_obj, dst_obj)):
            raise Exception(f'{src_obj} or {dst_obj} is invalid object')

        if protocol.upper() not in ['TCP', 'UDP', 'ICMP']:
            raise Exception(f'{protocol} is an invalid protol. Policy lookup only ')

        policies = Policy.get_policies(device, src, dst, src_obj, dst_obj, port, protocol, user)
        logger.info(f'Policies:\n{policies.__dict__}')
        if policies:
            allowed = policies.first().action
        output = [True, allowed, policies]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output


def get_interface_object(device, items):
    object = None
    for item in items:
        if item.zone:
            type = 'zone'
            obj = item.zone
            if not object:
                object = item.zone
        else:
            obj = item
            type = 'interface'
            if not object:
                object = item
        if object != obj:
            object = None
            break
    if object:
        try:
            object = Object.objects.get(fortigate=device, type=type, object_id=object.id)
        except Object.DoesNotExist:
            object = None
    return object



def get_objects_values(objects, to_str=False, model='Object'):
    data = []
    if model != 'Object':
        if model == 'UserGroup':
            for obj in objects:
                data.extend(get_objects_values(obj.member.all()))
        else:
            data = [obj.name for obj in objects]
        return ', '.join(data) if to_str else data

    for obj in objects:
        obj_type = obj.type.lower()

        if obj_type in ['address group', 'service group', 'virtual ip group', 'schedule group']:
            data.extend(get_objects_values(obj.object.member.all()))
        
        elif obj_type == 'address':
            val = get_address_values(obj.object)
            if val:
                data.append(val)

        elif obj_type == 'service':
            val = get_service_values(obj.object)
            if val:
                data.extend(val if isinstance(val, list) else [val])

        elif obj_type == 'virtual ip':
            val = get_vip_values(obj.object)
            if val:
                data.append(val)

        elif obj_type == 'schedule onetime':
            val = get_schedule_values(obj.object)
            if val:
                data.append(val)

        elif obj_type == 'schedule recurring':
            val = get_schedule_values(obj.object, recurring=True)
            if val:
                data.append(val)

        else:
            data.append(obj.name)

    return ', '.join(data) if to_str else data


def get_address_values(obj):
    if obj.type == 'ipmask':
        return 'ALL' if str(obj.subnet) == '0.0.0.0/0' else str(obj.subnet)
    elif obj.type == 'iprange':
        return f'{obj.start_ip}-{obj.end_ip}'
    return obj.fqdn


def get_service_values(obj):
    if 'SOCKS' not in obj.protocol and ('TCP' in obj.protocol or 'UDP' in obj.protocol):
        parts = []
        if obj.tcp_portrange:
            parts.append(f"{', '.join([f'TCP/{port}' for port in obj.tcp_portrange.split()])}")
        if obj.udp_portrange:
            parts.append(f"{', '.join([f'UDP/{port}' for port in obj.udp_portrange.split()])}")
        return parts
    return obj.name


def get_vip_values(obj):
    if obj.external_address:
        return get_address_values(obj.external_address)
    if obj.external_ip and obj.external_ip != '0.0.0.0':
        return obj.external_ip
    return obj.name


def get_schedule_values(obj, recurring=False):
    if not recurring:
        return f'From {timezone.localtime(obj.start).strftime("%b-%d-%Y %H:%M")} to {timezone.localtime(obj.end).strftime("%b-%d-%Y %H:%M")}'

    days_list = obj.day.title().split()
    days = classify_days(days_list)
    all_time = str(obj.start) == '00:00:00' and str(obj.end) == '00:00:00'

    if days == 'Everyday' and all_time:
        return 'Always'
    if all_time:
        return f'Every {days}'
    return f'Every {days} from {obj.start.strftime("%I:%M %p")} to {obj.end.strftime("%I:%M %p")}'


def classify_days(days_list):
    if len(days_list) == 7:
        return 'Everyday'
    if len(days_list) == 5 and 'Sunday' not in days_list and 'Saturday' not in days_list:
        return 'Weekdays'
    if len(days_list) == 2 and 'Sunday' in days_list and 'Saturday' in days_list:
        return 'Weekends'
    return ', '.join(days_list)