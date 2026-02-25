import logging
import sys
import re

from django.db.models import Q, F, Func, Value, ExpressionWrapper, Case, When, BooleanField
from django.db.models.fields import GenericIPAddressField
from django.utils import timezone

from ..models import *
from .find_policy import find_policy
from ipaddress import ip_address, ip_network
from typing import List, Dict, Optional

logger = logging.getLogger('route')

__all__ = (
    'find_route',
    'find_path',
    'find_longest_matched',
    'sort_subnets',
    'find_nearest_to_the_source',
    'getInterfaces'
)

def getInterfaces(fortigate_id):
    data = Interfaces.objects.all().filter(is_decommissioned=False)
    if fortigate_id:
        data = data.filter(device__id=fortigate_id)
    return data

def find_route(address, device=None, interface=None, type=None, src=None):
    """
    Find the routes of an IP/Network address in routing table in the network
    :param address: string
    :param device: device object
    :param interface: interface object
    :param type: string, [connect, ospf, static, etc.]
    :return: return a route object
    """
    output = [False, 'Unknown']
    found = False
    try:
        logger.info(f'Looking for {address} {f'in {str(device)} routing table' if device else ''}')
        result = RoutingTable.objects.filter(route__net_contains_or_equals=address)
        if device:
            result = result.filter(interface__fortigate=device)
        if interface:
            result = result.filter(interface=interface)
        if type:
            status = result.filter(type=type)
            if type == 'connect':
                if len(status) > 1:
                    found = True
                    if src:
                        # for network that in broadcast domain
                        status = find_nearest_to_the_source(status, src)
                        if not status[0]:
                            raise Exception(status[1])
                        if len(status[1]) > 1:
                            found = False
                        status = status[1]
                    else:
                        raise Exception(f'No source address provided')
                # if no connected routes found
                elif not status and src:
                    status = remove_invalid_route(result, address, src)
                    if not status[0]:
                        raise Exception(status[1])
                    status = status[1]
            if status:
                result = status

        if result and len(result) > 1:
            status = find_longest_matched(address, result, type, found=found, src=src, device=device)
            if not status[0]:
                raise Exception(status[1])
            result = status[1]
        if not result:
            raise Exception(f'No route entry found for {address}{' in ' + str(device) if device else ''}')
        output = [True, result]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output



def find_longest_matched(address, routes, type='connect', found=True, src=None, device=None):
    output = [False, 'Unknown']
    items = []
    try:
        logger.info(f'Find longest matched for {address} {f'in {str(device)} routing table' if device else ''}')
        if not routes:
            raise Exception("No routes provided.")
        # items = sort_subnets(routes)[0]
        items = filter_best_routes(address, routes, device)
        if items:
            devices = []
            if type == 'connect':
                logger.info(f'Looking for {address}')
                msg = ''
                tmp = []
                for item in items:
                    if not item.next_hop:
                        if item.interface.name == 'Null':
                            continue
                        tmp.append(item)
                        if item.interface.fortigate not in devices:
                            devices.append(item.interface.fortigate)
                        if msg:
                            msg = f'{routes}\n{item} from {item.interface}'
                        else:
                            msg = f'{item} from {item.interface}'
                items = tmp
                if not devices and src:
                    status = find_routes_from_source(address, src)
                    if not status[0]:
                        raise Exception(status[0])
                    items = status[1]
                elif len(devices) > 1 and found:
                    logger.debug(f'Routes ({address}) found on multiple devices \n{msg}')
                    raise Exception(f'Routes ({address}) found on multiple devices')
                elif len(devices) > 1 and src and not found:
                    status = find_direct_routes(items, src)
                    if not status[0]:
                        raise Exception(status[1])
                    items = status[1]
                if not items:
                    raise Exception(f'Unable to find the route origin of {address}')
                logger.info(items)
        output = [True, items]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err), items]
    finally:
        return output

def filter_best_routes(address, routes, device=None):
    longest_matched = {}
    objects = {}
    prefixes = []
    ADs = []
    prefixlen = 0
    DO_NOT_CONTINUE = False
    logger.info(f'Find best route for {address} {f'in {str(device)} routing table' if device else ''}')
    if routes:
        for item in routes:
            if item.route.prefixlen >= prefixlen:
                prefixlen = item.route.prefixlen
                prefixes.append(prefixlen)
                if item.route.prefixlen in longest_matched:
                    longest_matched[item.route.prefixlen].append(item)
                else:
                    longest_matched[item.route.prefixlen] = [item]

    if longest_matched:
        prefixes.sort()
        longest_matched = longest_matched[prefixes[-1]]
        #  To remove routes that less priority if routes is on same device with same AD
        devices = {}
        for obj in longest_matched:
            device = obj.interface.fortigate
            if device in devices:
                if obj.type == devices[device].type:
                    if obj.priority < devices[device].priority:
                        longest_matched.remove(devices[device])
                    elif devices[device].priority < obj.priority:
                        longest_matched.remove(obj)
            else:
                devices[device] = obj
            # This is for environment has multiple protocol on edged devices.
            if obj.interface.fortigate.priority >= 5:
                DO_NOT_CONTINUE = True          

    if DO_NOT_CONTINUE:
        logging.info("Won't continue to check AD")
        return longest_matched
    
    if len(longest_matched) > 1:
        distance = 255
        # To remove routes with highest AD
        for item in longest_matched:
            if item.distance <= distance:
                distance = item.distance
                ADs.append(distance)
            if item.distance in objects:
                objects[item.distance].append(item)
            else:
                objects[item.distance] = [item]
        
        if objects:
            ADs.sort()
            objects = objects[ADs[0]]
    else:
        objects = longest_matched
    return objects


def sort_subnets(routes):
    objects = {}
    prefixes = []
    prefixlen = 0
    if routes:
        for item in routes:
            if item.route.prefixlen >= prefixlen:
                prefixlen = item.route.prefixlen
                prefixes.append(prefixlen)
                if prefixlen in objects:
                    objects[prefixlen].append(item)
                else:
                    objects[prefixlen] = [item]
    if objects:
        prefixes.sort()
        objects = objects[prefixes[-1]]
        #  To remove routes that less priority if routes is on same device with same AD
        devices = {}
        for obj in objects:
            device = obj.interface.fortigate
            if device in devices:
                if obj.type == devices[device].type:
                    if obj.priority < devices[device].priority:
                        objects.remove(devices[device])
                    elif devices[device].priority < obj.priority:
                        objects.remove(obj)
            else:
                devices[device] = obj
        return [objects, prefixes]
    return [False]


def find_nearest_to_the_source(items, src):
    output = [False, 'Unknown']
    data = []
    try:
        hops = {}
        for item in items:
            status = find_route(src, device=item.interface.fortigate)
            if not status[0]:
                raise Exception(status[1])
            hop = 0
            for i in status[1]:
                if i.next_hop:
                    if item not in data:
                        data.append(item)
                        tmp_devices = [i.next_hop.fortigate]
                        while True:
                            devices = tmp_devices
                            tmp_devices = []
                            for device in devices:
                                status = find_route(src, device=device)
                                if not status[0]:
                                    raise Exception(status[1])
                                for s in status[1]:
                                    if s.next_hop:
                                        tmp_devices.append(s.next_hop.fortigate)
                            if tmp_devices:
                                hop += 1
                            else:
                                break
                else:
                    if item not in data:
                        hop = -1
                        data.append(item)
            hops[item] = hop
        if len(data) > 1 and hops:
            # hop = -2
            hop = []
            objects = {}
            for k, v in hops.items():
                if v not in hop:
                    hop.append(v)
                if v in objects:
                    objects[v].append(k)
                else:
                    objects[v] = [k]
                hop.append(v)
            if objects:
                hop.sort()
                data = objects[hop[0]]
                """if hop == -2:
                    hop = v
                    route = [k]
                elif v <= hop:
                    hop = v
                    route = [k]
            data = routes"""
        output = [True, data]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output


def find_direct_routes(items, src):
    output = [False, 'Unknown']
    data = []
    try:
        devices = {}
        tmp = []
        logger.info('Finding directly connected routes')
        for item in items:
            devices[item.interface.fortigate] = item
        for item in items:
            # remove routes from less priority devices
            if item.interface.fortigate.priority <= 1:
                tmp.append(item)
            # find routes if destination is nearest from the source
            status = find_route(src, device=item.interface.fortigate, type='connect')
            if not status[0]:
                continue
            for i in status[1]:
                if i.interface.fortigate in devices and i.type == "connect" and item not in data:
                    data.append(item)
        if not data:
            data = tmp
        output = [True, data]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output


def find_routes_from_source(address, src):
    output = [False, 'Unknown']
    routes = []
    try:
        devices = []
        logger.info(f'Looking for {address}')
        status = find_route(src, type="connect", src=address)
        if not status[0]:
            raise Exception(status[1])
        if len(status[1]) > 1:
            raise Exception('Unable to find source')
        for item in status[1]:
            devices.append(item.interface.fortigate)
        while True:
            tmp_devices = devices
            devices = []
            for device in tmp_devices:
                status = find_route(address, device=device)
                if not status[0]:
                    raise Exception(status[1])
                for item in status[1]:
                    if not item.next_hop:
                       routes.append(item)
                    else:
                        devices.append(item.next_hop.fortigate)
            if routes:
                break
        output = [True, routes]
    except Exception as err:
        logger.exception(err)
        # print(err)
        output = [False, str(err)]
    finally:
        return output


def remove_invalid_route(items, dst, src):
    output = [False, 'Unknown']
    try:
        logger.info(f'Removing invalid routes for {dst}')
        data = items = filter_best_routes(dst, items)
        for item in items:
            LOOP = True
            devices = [item.interface.fortigate]
            while LOOP:
                if devices:
                    for device in devices:
                        status = find_route(src, device=device)
                        if not status[0]:
                            raise Exception(status[1])
                        for i in status[1]:
                            tmp_devices = []
                            if i.next_hop:
                                status = find_route(dst, device=i.next_hop.fortigate)
                                if not status[0]:
                                    raise Exception(status[1])
                                for d in status[1]:
                                    if d.next_hop and d.next_hop.fortigate not in devices:
                                        # data = data.exclude(pk=item.id)
                                        if data:
                                            if isinstance(data, list):
                                                data = data.remove(item)
                                            else:
                                                data = data.exclude(pk=item.id)
                                        LOOP = False
                                        break
                                    tmp_devices.append(d.interface.fortigate)
                                if not LOOP:
                                    break
                        if not LOOP:
                            break
                    devices = tmp_devices
                else:
                    break
            # print(f'data: {data}')
        output = [True, data]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output


def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj



class NetworkPathResolver:
    def _find_route(self, address, device: Optional[Fortigate]=None, destination: Optional[str]=None, connected: Optional[bool]=False):
        queryset = RoutingTable.objects.filter(route__net_contains_or_equals=address)

        if device:
            queryset = queryset.filter(fortigate=device)

        if connected:
            qs = queryset.filter(type__in=['connect', 'local'])
            if qs.exists():
                # for multiple connected routes
                if qs.count() > 1:
                    candidate_device_ids = list(qs.values_list("fortigate_id", flat=True).distinct())
                    valid_sources = []
                    for q in qs:
                        best_routes = self._find_route(destination, q.fortigate)
                        for route in best_routes:
                            if not route.gateway:
                                continue
                            if route.next_hop and route.next_hop.id in candidate_device_ids:
                                if route.next_hop.id not in valid_sources:
                                    valid_sources.append(route.next_hop.id)
                                break
                    if valid_sources:
                        return qs.filter(fortigate_id__in=valid_sources)
                else:
                    return qs

            queryset = queryset.exclude(next_hop__isnull=False)

        if not queryset.exists():
            return RoutingTable.objects.none()

        candidates = queryset.order_by('-route', 'distance', 'metric')
        best_score = (-candidates[0].route.prefixlen, candidates[0].distance, candidates[0].metric)
        routes = [r for r in candidates if (-r.route.prefixlen, r.distance, r.metric) == best_score]

        candidate_devices = set([r.fortigate for r in routes])
        if len(candidate_devices) > 1:
            routes = self._find_direct_routes(routes, destination)
            candidate_devices = set([r.fortigate for r in routes])
            if len(candidate_devices) != 1:
                candidates = queryset.exclude(device__role__in=['edge']).order_by('-route', 'distance', 'metric')
                best_score = (-candidates[0].route.prefixlen, candidates[0].distance, candidates[0].metric)
                routes = [r for r in candidates if (-r.route.prefixlen, r.distance, r.metric) == best_score]
            candidate_devices = set([r.fortigate for r in routes])
            # Find shortest path to the destination, last resort for multiple routes that no connected routes
            if len(candidate_devices) > 1 and connected:
                candidates = queryset.filter(
                    next_hop__isnull=True
                ).exclude(device__role__in=['edge']).order_by('-route', 'distance', 'metric')
                routes = self._find_shortest_path(candidates, destination)

        return routes

    def _find_direct_routes(self, routes: List[RoutingTable], destination: str) -> List[RoutingTable]:
            valid_routes = []
            for route in routes:
                best_routes = self._find_route(destination, device=route.fortigate, connected=True)
                for r in best_routes:
                    if not r.gateway and route.fortigate == r.fortigate:
                        valid_routes.append(route)
                        continue
            return valid_routes

    def _find_shortest_path(self, routes: List[RoutingTable], destination: str) -> List[RoutingTable]:
        hops = set()
        data = {}
        for route in routes:
            result = self._trace_routes(route.fortigate, destination, set(), {})
            hop = len(result)
            hops.add(hop)
            if hop not in data:
                data[hop] = [route]
            else:
                data[hop].append(route)

        if not hops:
            return []

        return data[sorted(hops)[0]]

    def _trace_routes(self, device, destination_ip: str, visited: set, path_map: dict, incoming_interfaces: Optional[List[Interfaces]] = None) -> Dict:
        if device in visited:
            return {"error": f"Loop detected at device {str(device)}"}

        visited.add(device)
        routes = self._find_route(destination_ip, device)
        if not routes:
            return {"device": device, "src": incoming_interfaces or [], "dst": [], "info": "No route found"}

        outgoing = []
        next_hops = []

        for route in routes:
            if route.interface:
                outgoing.append(route.interface)

            if route.next_hop and route.next_hop != device:
                next_hops.append((route.next_hop, [route.next_hop_interface], device))

        path_map[device] = path_map.get(device, {"src": [], "dst": []})
        path_map[device]["src"].extend([i for i in incoming_interfaces or [] if i and i not in path_map[device]["src"]])
        path_map[device]["dst"].extend([i for i in outgoing if i not in path_map[device]["dst"]])

        for next_device, next_hop_interface, src_device in next_hops:
            path_map[next_device] = path_map.get(next_device, {"src": [], "dst": []})
            path_map[next_device]["src"].extend([i for i in next_hop_interface if i and i not in path_map[next_device]["src"]])

            self._trace_routes(next_device, destination_ip, visited.copy(), path_map, next_hop_interface)

        return path_map

    def resolve_path(self, source_ip: str, destination_ip: str) -> Dict[Fortigate, Dict[str, List[Interfaces]]]:
        visited = set()
        path_map = {}

        source_routes = self._find_route(source_ip, destination=destination_ip, connected=True)
        if not source_routes:
            return {"error": f"Source IP {source_ip} not found in routing table"}

        destination_routes = self._find_route(destination_ip, destination=source_ip, connected=True)
        destination_interfaces = []
        destination_devices = set()
        for route in destination_routes:
            destination_devices.add(route.fortigate)
            destination_interfaces.append(route.interface)

        for route in source_routes:
            intf = route.interface
            self._trace_routes(route.fortigate, destination_ip, visited.copy(), path_map, [intf] if intf else [])

        return path_map


def find_path(src, dst):
    try:
        resolver = NetworkPathResolver()
        paths = resolver.resolve_path(src, dst)
        # for path in paths:
        #     print(path)
        return [True, paths]
    except Exception as err:
        logger.exception(err)
        return [False, str(err)]

