import logging
import sys
import collections
import inspect
import pytz

from django.utils import timezone
from django.conf import settings
from django.db.models import ForeignKey, DateTimeField, TimeField, JSONField, PositiveBigIntegerField, PositiveSmallIntegerField

from datetime import datetime

from ..utils.api import API
from ..utils.settings import get_plugin_default
from ..models import *
from netbox.encryption import decrypt

logger = logging.getLogger(__name__)
local_tz = pytz.timezone(settings.TIME_ZONE)

__all__ = (
    'update_inventory',
)

def device_matches_constraints(device, config):
    """
    Determine if the device matches the constraints defined in config.
    - If config is True, we apply globally (True).
    - If config is False or None, we return False.
    - If config is a dictionary:
      - If 'constrains' is not defined in config, we apply globally (True).
      - If 'constrains' is defined, we require at least one match if there are active constraint lists.
      - If all constraint lists are empty, we return False.
    """
    if config is True:
        return True
    if config is False or config is None:
        return False
        
    if not isinstance(config, dict):
        return False
        
    if 'constrains' not in config:
        return True
        
    constrains = config.get('constrains', {}) or {}
    devices = [d.lower() for d in constrains.get('devices', []) if d]
    roles = [r.lower() for r in constrains.get('roles', []) if r]
    tags = [t.lower() for t in constrains.get('tags', []) if t]
    
    # If they defined 'constrains' but all lists are empty, it matches nothing.
    if not devices and not roles and not tags:
        return False
        
    if devices and device.device.name.lower() in devices:
        return True
        
    if roles and device.role.lower() in roles:
        return True
        
    if tags:
        device_tags = [t.lower() for t in device.device.tags.values_list('slug', flat=True)]
        if any(tag in device_tags for tag in tags):
            return True
            
    return False

def update_inventory(fg, DEBUG=False, job=None):
    output = [False, 'Unknown']
    module = None
    vdom = None
    items = []
    state = 'Failed'
    logger = logging.getLogger(__name__) # fallback logger
    try:
        # Initialize connection to Fortigate device
        hostname = fg.device.name
        data = {
            'ip': fg.mgmt_ip.address.ip,
            'username': get_plugin_default('fortigates_username'),
            'password': decrypt(get_plugin_default('fortigates_password')),
            'port': fg.api_port,
            'device': hostname,
            'vdom': fg.default_vdom
        }

        FORTIGATE = API.get(fg.fortios_version.strip(), None)
        if not FORTIGATE:
            raise Exception(f"No available API client for FortiOS {fg.fortios_version}")
        
        module = FORTIGATE(data, DEBUG)
        
        logger = module.logger

        if module.ERROR:
            raise Exception(module.ERROR)
        
        

        device_data = {
            'version': module.version,
            'hostname': module.hostname,
            'vdom': module.vdom
        }
            
        status = update_device(fg, device_data, logger=logger, job=job)
        if not status[0]:
            raise Exception(status[1])

        # List of categories to fetch and update
        categories = [
            ('interfaces', module.get_interfaces, Interfaces, update_object),
            ('zones', module.get_zones, Zone, update_object),
            ('ipv4_routes', module.get_routing_table, RoutingTable, update_routing_table),
            ('addresses', module.get_address_objects, Address, update_object),
            ('address_groups', module.get_address_groups, AddressGroup, update_object),
            ('services', module.get_services, Services, update_object),
            ('service_groups', module.get_service_groups, ServiceGroup, update_object),
            ('vip', module.get_vip, VIP, update_object),
            ('vip_groups', module.get_vip_groups, VIPGroup, update_object),
            ('schedule_onetime', module.get_schedule_onetime, ScheduleOnetime, update_object),
            ('schedule_recurring', module.get_schedule_recurring, ScheduleRecurring, update_object),
            ('schedule_groups', module.get_schedule_groups, ScheduleGroup, update_object),
            ('profile_groups', module.get_profile_groups, ProfileGroup, update_object),
            ('authentication_servers', module.get_authentication_servers, AuthenticationServer, update_object),
            ('users', module.get_users, User, update_object),
            ('user_groups', module.get_user_groups, UserGroup, update_object),
            ('policies', module.get_policies, Policy, update_object)
        ]
        
        
        skip_inventory = get_plugin_default('skip_inventory', {}) or {}
        inventory_config = skip_inventory.get('inventory', {}) or {}

        # Loop through and update each category
        BREAK = False
        error_with = ''
        ERROR = ''
        for category_name, fetch_method, model, update_method in categories:
            # Check if this category is configured to be skipped entirely for this device
            category_cfg = None
            for key in [category_name, 'routing_table' if category_name == 'ipv4_routes' else None]:
                if key and key in inventory_config:
                    category_cfg = inventory_config[key]
                    break
            
            # Skip the entire category if constraints match and "types" is not specified
            if category_cfg is not None and 'types' not in (category_cfg if isinstance(category_cfg, dict) else {}):
                if device_matches_constraints(fg, category_cfg):
                    msg = f"Skipped category '{category_name}' per configuration constraints."
                    if job:
                        job.logger.info(f"{hostname}: {msg}")
                    logger.info(f"{hostname}: {msg}")
                    d = {'device': hostname, 'type': category_name, 'status': 'Skipped', 'errors': []}
                    items.append(d)
                    if state == 'Failed':
                        state = 'Successful'
                    continue

            d = {'device': hostname, 'type': category_name, 'status': 'Successful', 'errors': []}
            if not BREAK:
                status = update_category(category_name, module, fg, fetch_method, update_method, model, logger=logger)
                if not status[0]:
                    BREAK = True
                    ERROR = status[1]
                    error_with = category_name
            else:
                status = [False, f'Unable to continue due {ERROR} in {error_with}']
            if not status[0]:
                if state == 'Successful':
                    state = 'Successful with Errors'
                d['status'] = 'Failed'
                d['errors'] = [status[1]]
                items.append(d)
                if job:
                    job.logger.error(f"{hostname}: {status[1]}")
            elif len(status) == 3:
                state = d['status'] = 'Successful with Errors'
                d['errors'] = status[2]
                items.append(d)
                if job:
                    job.logger.warning(f"{hostname}: Pulling {category_name} of {hostname} has completed with errors.")
                    job.logger.warning(f"{hostname} - Errors: {status[2]}")
            if state == 'Failed' and status[0]:
                state = 'Successful'
            if job and status[0]:
                job.logger.info(f"{hostname}: Pulling {category_name} of {hostname} has successfully completed.")
            
        if state ==  'Successful':
            items = [{'device': hostname, 'type': 'All Inventory', 'status': 'All Successful'}]
            
        output = [True, state, items]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err), items]
    finally:
        if module:
            module.close_session()
        return output


def update_device(fortigate=None, data={}, logger=logger, job=None):
    """
        To update Device data
    """
    output = [False, 'Unknown']
    changes = []
    
    try:
        updated_time = timezone.localtime()
        if not fortigate:
            raise Exception('No device')
        hostname = fortigate.device.name
        if fortigate.default_vdom != 'root' and fortigate.default_vdom not in fortigate.device.name:
            hostname = f"{fortigate.device.name} - {fortigate.default_vdom}"
        if data:
            if fortigate and hasattr(fortigate, 'snapshot'):
                fortigate.snapshot()
            if data['version'] and data['version'] != fortigate.fortios_version:
                changes.append(f'{updated_time.strftime('%Y-%b-%d %H:%m')}: Changing OS Version from "{fortigate.fortios_version}" to "{data['version']}"')
                msg = f'{fortigate}: Changing OS Version from "{fortigate.fortios_version}" to "{data['version']}"'
                if job:
                    job.logger.info(msg)
                logger.info(msg)
                fortigate.fortios_version = data['version']
            if data['vdom'] and data['vdom'] != fortigate.default_vdom:
                changes.append(f'{updated_time.strftime('%Y-%b-%d %H:%m')}: Changing VDOM from "{fortigate.default_vdom}" to "{data['vdom']}"')
                msg = f'{fortigate}: Changing VDOM from "{fortigate.default_vdom}" to "{data['vdom']}"'
                if job:
                    job.logger.info(msg)
                logger.info(msg)
                fortigate.default_vdom = data['vdom']
            if data['hostname']:
                hname = f"{data['hostname']} - {data['vdom']}" if data['vdom'] != 'root' else data['hostname']
                if hname != hostname and get_plugin_default('SYNC_HOSTNAME', True):
                    msg = f'{fortigate}: Changing hostname from "{hostname}" to "{hname}"'
                    if hasattr(fortigate.device, 'snapshot'):
                        fortigate.device.snapshot()
                    fortigate.device.name = hname
                    if job:
                        job.logger.info(msg)
                        fortigate.device._changelog_message = f"Update by Job ID: {job.job.pk}"
                    logger.info(msg)
                    fortigate.device.save()
            if changes:
                if job:
                    fortigate._changelog_message = f"Update by Job ID: {job.job.pk}"
                fortigate.save()
        output = [True, 'Success']
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output


def update_routing_table(device=None, data={}, logger=logger):
    """
    To update Fortigate Routing Table
    """
    output = [False, 'Unknown']
    try:
        if not device and not data:
            raise Exception('No device or data provided')
        route_ids = list(RoutingTable.objects.filter(interface__fortigate=device).values_list('id', flat=True))
        errors = []
        
        # Determine route types to skip for this device
        skip_inventory = get_plugin_default('skip_inventory', {}) or {}
        inventory_config = skip_inventory.get('inventory', {}) or {}
        category_cfg = None
        for key in ['ipv4_routes', 'routing_table']:
            if key in inventory_config:
                category_cfg = inventory_config[key]
                break
        
        skip_types = set()
        if category_cfg is not None and isinstance(category_cfg, dict) and 'types' in category_cfg:
            if device_matches_constraints(device, category_cfg):
                skip_types = {t.lower() for t in category_cfg.get('types', []) if t}

        for address in data:
            for item in data[address]:
                if item.get('type', '').lower() in skip_types:
                    continue
                changes = []
                item['next_hop'] = None
                try:
                    interface = Interfaces.objects.get(fortigate=device, name=item['interface'])
                except Interfaces.DoesNotExist:
                    logger.warning(f'Unable to add route ({address}:{item}). Missing object ({item['interface']})')
                    errors.append(f'Unable to add route ({address}:{item}). Missing object ({item['interface']})')
                    continue
                if item['gateway']:
                    qs = Interfaces.objects.filter(ip__net_host=item['gateway'], is_decommissioned=False, enabled=True)
                    if qs.count() > 1:
                        logger.warning(
                            f'Unable to identify next hop for "{address}"   due to multiple interface with IP address "{item['gateway']}": {", ".join([f"{i.device} - {i.name} ({i.id})" for i in qs])}')
                        errors.append(
                            f'Unable to identify next hop for "{address}" due to multiple interface with IP address "{item['gateway']}": {", ".join([f"{i.device} - {i.name} ({i.id})" for i in qs])}')
                        continue
                    elif qs.exists():
                        item['next_hop'] = qs.first().fortigate
                # Set routes AD to 200 for unknown next_hop
                if item['next_hop'] is None and len(data[address]) == 1:
                    if device.role == 'edge' and item['type'] not in ['connect', 'local']:
                        item['distance'] = 200
                try:
                    updated_time = timezone.localtime()
                    route = RoutingTable.objects.get(interface=interface, route=address) # need to add gateway
                    key_dict = route.__dict__
                    key_dict['interface'] = route.interface.name
                    # if key_dict['gateway'] is None:
                    key_dict['gateway'] = '' if key_dict['gateway'] is None else key_dict['gateway'].ip
                    
                    if key_dict['next_hop_id'] is None:
                        key_dict['next_hop'] = None
                    else:
                        key_dict['next_hop'] = route.next_hop
                    keys = ['type', 'gateway', 'interface', 'distance', 'priority', 'metric', 'next_hop']
                    for key in keys:
                        if str(key_dict[key]) != str(item[key]):
                            changes.append(f'{updated_time.strftime('%Y-%b-%d %H:%m')}: Changing {key} from {str(key_dict[key])} to {item[key]}')
                            logger.info(f'{route.id}: Changing {address} {key} from {str(key_dict[key])} to {item[key]}')
                except RoutingTable.DoesNotExist:
                    logger.info(f'Creating "{address}" route')
                    route = RoutingTable.objects.create(
                        fortigate=device,
                        route=address,
                        type=item['type'],
                        gateway=item['gateway'],
                        next_hop=item['next_hop'],
                        interface=interface,
                        distance=item['distance'],
                        priority=item['priority'],
                        metric=item['metric']
                    )
                if changes:
                    if route.pk and hasattr(route, 'snapshot'):
                        route.snapshot()
                    route.fortigate = device
                    route.type = item['type']
                    route.gateway = item['gateway']
                    route.next_hop = item['next_hop']
                    route.distance = item['distance']
                    route.priority = item['priority']
                    route.metric = item['metric']
                    route.interface = interface
                    route._changelog_message = "Inventory updated by job."
                    route.save()
                if route.id in route_ids:
                    route_ids.remove(route.id)
        for id in route_ids:
            RoutingTable.objects.get(id=id).delete()
        if errors:
            output = [True, 'Successful with Errors', errors]
        else:
            output = [True, 'Successful']
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output

def update_object(model, device=None, data={}, logger=logger):
    output = [False, 'Unknown']
    errors = []
    try:
        if not device or not data:
            raise ValueError('No device or data provided')

        object_ids = list(model.objects.filter(fortigate=device).values_list('id', flat=True))

        # Cache ForeignKey and Many-to-Many fields
        foreign_keys = {
            field.name: field.related_model
            for field in model._meta.fields
            if isinstance(field, ForeignKey) and field.name != 'fortigate'
        }

        for item in data.values():
            changes = []
            updated_time = timezone.localtime()
            # Resolve ForeignKeys
            for fk_field, fk_model in foreign_keys.items():
                if fk_field in item:
                    item[fk_field] = fk_model.objects.filter(fortigate=device, name=item[fk_field]).first()

            # Fetch existing object or create a new one
            name = item['name']
            if model.__name__ == 'Policy':
                obj = model.objects.filter(fortigate=device, policyid=item['policyid']).first()
                name = f'PID:{item['policyid']}'    
            else:
                obj = model.objects.filter(fortigate=device, name=item['name']).first()
            is_new = obj is None

            obj_name = obj.name if obj and obj.name else name

            if is_new:
                logger.info(f'{model.__name__}: Creating "{name}" {model.__name__}')
                m2m_fields = {field.name: item.pop(field.name, []) for field in model._meta.many_to_many}  # Extract M2M fields
                try:
                    obj = model.objects.create(fortigate=device, **item) # Create object first
                except Exception as err:
                    errors.append(f'{model.__name__}: Unable to create {model.__name__} object due to {err} \nData: {item}')
                    logging.exception(f'{model.__name__}: Unable to create {model.__name__} object due to {err} \nData: {item}')
                    continue
                logger.info(f'{model.__name__}:{obj.id}: Created "{name}" {model.__name__}')
                # **Set Many-to-Many relationships after saving**
                for m2m_field_name, values in m2m_fields.items():
                    related_objects = []
                    valid_types = None
                    
                    # Get the actual Many-to-Many field object
                    m2m_field = model._meta.get_field(m2m_field_name)
                    
                    if m2m_field.related_model.__name__ == 'Object':
                        related_field = m2m_field.related_model._meta.get_field(m2m_field.remote_field.name)
                        limit_choices = getattr(related_field, 'limit_choices_to', None)
                        
                        # If limit_choices_to exists and contains 'type__in', get the valid types
                        if limit_choices and 'type__in' in limit_choices:
                            valid_types = limit_choices['type__in']

                    for related_name in values:
                        try:
                            if valid_types:
                                related_obj = m2m_field.related_model.objects.get(name=related_name, fortigate=device, type__in=valid_types)
                            else:
                                related_obj = m2m_field.related_model.objects.get(name=related_name, fortigate=device)
                            related_objects.append(related_obj)
                        except m2m_field.related_model.DoesNotExist:
                            errors.append(f'{model.__name__}:{obj.id}: Unable to find {m2m_field_name} object: {related_name}')
                            logger.warning(f'{model.__name__}:{obj.id}: Unable to find {m2m_field_name} object: {related_name}')
                    
                    if related_objects:
                        getattr(obj, m2m_field_name).set(related_objects)  # Set M2M relationships
                        logger.info(f'{model.__name__}:{obj.id}: Set {m2m_field_name} for "{obj_name}" to {", ".join(str(o.name) for o in related_objects)}')
            else:
                # Handle is_decommissioned flag
                if obj.pk and hasattr(obj, 'snapshot'):
                    obj.snapshot()

                if obj.is_decommissioned:
                    obj.is_decommissioned = False
                    changes.append(f'{updated_time.strftime("%Y-%b-%d %H:%M")}: Changing status from Decommissioned to Active')
                    logger.info(f'{model.__name__}:{obj.id}: Changing "{item["name"]}" status from Decommissioned to Active')

                # Process fields excluding specific ones
                ignored_fields = {'id', 'fortigate', 'name', 'is_decommissioned', 'created', 'last_update'}
                for field in model._meta.fields:
                    try:
                        if field.name in ignored_fields:
                            continue
                        if field.name not in item:
                            continue
                        current_value = getattr(obj, field.name, None)
                        new_value = item.get(field.name, None)

                        # Ensure that None values are replaced with '' for non-ForeignKey fields
                        if current_value is None and not isinstance(obj._meta.get_field(field.name) , ForeignKey):
                            current_value = ''
                        

                        # Normalize DateTimeField values
                        if isinstance(field, DateTimeField):
                            if isinstance(current_value, datetime) and current_value.tzinfo is None:
                                current_value = timezone.make_aware(current_value)
                            current_value = current_value.astimezone(timezone.get_current_timezone()).strftime('%H:%M %Y/%m/%d') if current_value else None

                        # Normalize TimeField values
                        elif isinstance(field, TimeField):
                            current_value = current_value.strftime('%H:%M') if current_value else ''
                        
                        # Normalize JSONField values
                        elif isinstance(field, JSONField):
                            current_value = [tuple(sorted(d.items())) for d in current_value]
                            new_value = [tuple(sorted(d.items())) for d in new_value]

                        # Normalize IntegerField values
                        elif isinstance(field, (PositiveBigIntegerField, PositiveSmallIntegerField)):
                            if current_value == '':
                                current_value = None

                        # Compare values
                        # For fields that are lists (but not ManyToMany), if you have any
                        if isinstance(current_value, list) and collections.Counter(current_value) != collections.Counter(new_value):
                            changes.append(f'{updated_time.strftime("%Y-%b-%d %H:%M")}: Changing {field.name} from {current_value} to {new_value}')
                            logger.info(f'{model.__name__}:{obj.id}: Changing "{obj_name}" {field.name} from {current_value} to {new_value}')
                            setattr(obj, field.name, new_value)

                        # For normal fields
                        elif str(current_value) != str(new_value):
                            changes.append(f'{updated_time.strftime("%Y-%b-%d %H:%M")}: Changing {field.name} from {current_value} to {new_value}')
                            logger.info(f'{model.__name__}:{obj.id}: Changing "{obj_name}" {field.name} from {current_value} to {new_value}')
                            setattr(obj, field.name, new_value)
                    except Exception as err:
                        logger.error(f'{model.__name__}:{obj.id}: {err}\ncurrent: {current_value}\nnew: {new_value}')
                        errors.append(f'{model.__name__}:{obj.id}: {err}\ncurrent: {current_value}\nnew: {new_value}')
                        if changes:
                            obj.updated_time = updated_time
                        changes.append(str(err))
                        obj._changelog_message = "Inventory updated by job."
                        obj.save()
                        if getattr(settings,'ENV','DEV') == 'PROD':
                            continue
                    
                # Handle Many-to-Many relationships
                for field in model._meta.many_to_many:
                    m2m_field_name = field.name
                    if m2m_field_name in item:
                        # Get the current related objects
                        current_related = set(getattr(obj, m2m_field_name).all())
                        new_related = set()
                        # Add new related objects based on the provided data

                        valid_types = None
                        if field.related_model.__name__ == 'Object':
                            related_field = field.related_model._meta.get_field(field.remote_field.name)
                            limit_choices = getattr(related_field, 'limit_choices_to', None)
                            
                            # If limit_choices_to exists and contains 'type__in', get the valid types
                            if limit_choices and 'type__in' in limit_choices:
                                valid_types = limit_choices['type__in']
                            
                        for related_name in item[m2m_field_name]:
                            try:
                                if valid_types:
                                    related_obj = field.related_model.objects.get(name=related_name, fortigate=device, type__in=valid_types)
                                else:
                                    related_obj = field.related_model.objects.get(name=related_name, fortigate=device)
                                new_related.add(related_obj)
                            except field.related_model.DoesNotExist:
                                logger.warning(f'{model.__name__}:{obj.id}: Unable to find {m2m_field_name} object: {related_name}')
                                errors.append(f'{model.__name__}:{obj.id}: Unable to find {m2m_field_name} object: {related_name}')

                        # Determine which related objects to add and remove
                        to_add = new_related - current_related
                        to_remove = current_related - new_related
                        # Add new related objects
                        if to_add:
                            getattr(obj, m2m_field_name).add(*to_add)
                            changes.append(f'{updated_time.strftime("%Y-%b-%d %H:%M")}: Added {", ".join([str(o.name) for o in to_add])} to "{obj_name}" {m2m_field_name}')
                            logger.info(f'{model.__name__}:{obj.id}: Added {", ".join([str(o.name) for o in to_add])} to "{obj_name}" {m2m_field_name}')
                        # Remove old related objects
                        if to_remove:
                            getattr(obj, m2m_field_name).remove(*to_remove)
                            changes.append(f'{updated_time.strftime("%Y-%b-%d %H:%M")}: Removed {", ".join([str(o.name) for o in to_remove])} from "{obj_name}" {m2m_field_name}')
                            logger.info(f'{model.__name__}:{obj.id}: Removed {", ".join([str(o.name) for o in to_remove])} from "{obj_name}" {m2m_field_name}')
            # Save updates
            if changes:
                obj._changelog_message = "Inventory updated by job."
                obj.save()
            
            if obj.id in object_ids:
                object_ids.remove(obj.id)

        # Decommission leftover objects
        for obj in model.objects.filter(id__in=object_ids, is_decommissioned=False):
            obj.is_decommissioned = True
            obj._changelog_message = "Inventory updated by job."
            obj.save()
            obj_name = f'ID:{obj.id}' if not obj.name else obj.name
            logger.info(f'{model.__name__}:{obj.id}: Decommissioning "{obj_name}" {model.__name__}')

        if errors:
            output = [True, 'Successful with Errors', errors]
        else:
            output = [True, 'Successful']

    except Exception as err:
        logger.exception(f'{model.__name__}: {err}')
        output = [False, str(err)]
    
    return output



from django.contrib.contenttypes.models import ContentType

def resolve_related_object(related_name, device, logger=logger):
    """
    Resolve the related object dynamically based on its ContentType.
    This function uses the `GenericForeignKey` mechanism to get the correct object model.
    """
    # Here, the related_name should correspond to an instance name (e.g., 'Interface1', 'Address1', etc.)
    # You would need to know how to map the related name to the correct `ContentType` dynamically.
    try:
        # You might have the content type as part of the model or via another mechanism.
        content_type = ContentType.objects.get_for_model(related_name)
        related_model = content_type.model_class()

        # Fetch the related object by the name and device (assuming the name is unique per device)
        related_object = related_model.objects.get(name=related_name, device=device)
        return related_object
    except ContentType.DoesNotExist:
        logger.warning(f"ContentType not found for {related_name}")
        return None
    except related_model.DoesNotExist:
        logger.warning(f"Object with name {related_name} does not exist in {related_model}")
        return None
    except Exception as e:
        logger.error(f"Error resolving related object: {e}")
        return None
    

def update_category(category_name, module, device, fetch_method, update_method, model, logger=logger):
    """
    Helper function to fetch and update categories dynamically.
    """
    output = [False, 'Unknown']
    try:
        status = fetch_method()  # Fetch the data
        if not status[0]:
            raise Exception(f'Error fetching {category_name}: {status[1]}')

        data = getattr(module, category_name)  # Get dynamically updated data from module
        if data:
            # Get argument count for update_method
            params = inspect.signature(update_method).parameters
            param_count = len(params)

            if param_count == 4:
                status = update_method(model, device, data, logger)  # Standard case
            elif param_count == 3:
                status = update_method(device, data, logger)  # Some functions might not need `model`
            else:
                raise Exception(f'Unexpected argument count ({param_count}) for {update_method.__name__}')
            if not status[0]:
                raise Exception(f'Error updating {category_name}: {status[1]}')
            logger.info(f'{category_name} updated successfully.')
            output = status
        else:
            output = [True, 'Successful']
    except Exception as e:
        logger.exception(f'{str(e)}')
        output = [False, str(e)]
    return output

    