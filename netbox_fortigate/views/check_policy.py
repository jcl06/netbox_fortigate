from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.templatetags.static import static
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from django.utils import timezone

from ..utils.policy_lookups import is_connection_allowed, get_objects_values
from ..models import FortiGateDevice, FortiGatePolicy, FortiGateObject

import logging
import json

from ..utils.misc import getInterfaces

logger = logging.getLogger(__name__)

__all__ = (
    "DrawPathView",
    "PolicyView"
)

class Error(Exception):
    pass

class APIError(Exception):
    pass

import json
import logging

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import PermissionRequiredMixin

from ..forms import CheckPolicyForm

logger = logging.getLogger(__name__)


class DrawPathView(PermissionRequiredMixin, View):
    permission_required = "dcim.view_device"
    template_name = "netbox_fortigate/check_policy_form.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context={})

    def post(self, request, *args, **kwargs):
        form = CheckPolicyForm(request.POST)

        if not form.is_valid():
            # Return a single readable error string
            msg = "; ".join(
                [f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()]
            )
            return JsonResponse({"status": "Failed", "message": msg}, status=400)

        src = form.cleaned_data["src"]
        dst = form.cleaned_data["dst"]
        protocol = form.cleaned_data["protocol"]
        port = form.cleaned_data["port"]
        username = (form.cleaned_data.get("username") or "").strip()

        auth_type = "user" if username else ""
        icmptype = port if protocol == "icmp" else None

        try:
            submission_count = track_submission(request, src, dst, protocol, port, username)

            status = is_connection_allowed(
                src, dst, protocol, port, auth_type, username, icmptype, submission_count
            )
            if not status[0]:
                return JsonResponse({"status": "Failed", "message": str(status[1])}, status=400)

            policies = status[1]
            path = status[2]

            items = [{
                "name": src,
                "type": "host",
                "image": "img/host.png",
                "ip": "",
                "role": "src_host",
                "class": "node",
                "status": "allow",
                "policy_id": "",
            }]

            for fortigate, value in path.items():
                src_intf = value["src"][0]
                dst_intf = value["dst"][0]

                if policies[fortigate]["status"] == "allow":
                    policy_id = policies[fortigate]["policies"]["allow"][0]
                elif policies[fortigate]["policies"]["deny"]:
                    policy_id = policies[fortigate]["policies"]["deny"][0]
                else:
                    policy_id = "Implicit Deny"

                items.append({
                    "name": fortigate.device.name,
                    "type": "node",
                    "ip": fortigate.ip_address,
                    "role": fortigate.role.lower(),
                    "class": "node fortigate",
                    'image': "img/fortigate.png",
                    "interfaces": [
                        src_intf.zone.name if src_intf.zone and not src_intf.zone.is_decommissioned else src_intf.name,
                        dst_intf.zone.name if dst_intf.zone and not dst_intf.zone.is_decommissioned else dst_intf.name,
                    ],
                    "status": policies[fortigate]["status"],
                    "policy_id": policy_id,
                    "fortigate_id": fortigate.id,
                })

            items.append({
                "name": dst,
                "type": "host",
                "image": "img/host.png",
                "ip": f"{protocol.upper()}/{port}" if protocol != "icmp" else f"{protocol.upper()}/{port}",
                "role": "dst_host",
                "class": "node",
                "status": "allow",
                "policy_id": "",
            })

            topo_status = draw_topology(items)
            if not topo_status[0]:
                return JsonResponse({"status": "Failed", "message": str(topo_status[1])}, status=500)

            context = topo_status[1]
            context.update({
                "status": "Success",
                "src": src,
                "dst": dst,
                "protocol": protocol,
                "port": port,
            })
            return JsonResponse(context)

        except Exception as err:
            logger.exception(err)
            return JsonResponse({"status": "Failed", "message": "Internal error."}, status=500)

@csrf_exempt
def draw_path(request):
    data = None
    try:
        if request.method == 'GET':
            context = {}
            return render(request, 'netbox_fortigate/check_policy_form.html', context=context)
        data = json.loads(request.POST['data'])
        if 'src' not in data:
            logger.info("Key (src) not found\n{0}".format(data))
            raise Error("Invalid Request")
        src = data['src']
        if 'dst' not in data:
            logger.info("Key (dst) not found\n{0}".format(data))
            raise Error("Invalid Request")
        dst = data['dst']
        if 'protocol' not in data:
            logger.info("Key (protocol) not found\n{0}".format(data))
            raise Error("Invalid Request")
        protocol = data['protocol']
        if 'port' not in data:
            logger.info("Key (port) not found\n{0}".format(data))
            raise Error("Invalid Request")
        auth_type = ''
        username = ''
        # if 'auth_type' in data:
        #     if data['auth_type']:
        #         auth_type = data['auth_type']
        if 'username' in data:
            if data['username']:
                username = data['username']
                auth_type = 'user'
        port = data['port']
        if protocol != 'icmp' and not port:
            raise APIError("Port number is empty")
        icmptype = None
        if protocol == 'icmp':
            icmptype = port
        if not src:
            raise APIError("Source Address is empty")
        if not dst:
            raise APIError("Destination Address is empty")
        
        # Track submission count
        submission_count = track_submission(request, src, dst, protocol, port, username)
        logger.info(f"Submission count for ({src}, {dst}, {protocol}, {port}, {username}): {submission_count}")

            
        status = is_connection_allowed(src, dst, protocol, port, auth_type, username, icmptype, submission_count)
        if not status[0]:
            raise APIError(status[1])
        policies = status[1]
        path = status[2]
        items = [
            {
                "name": src,
                "image": "img/host.png",
                "type": "host",
                "ip": "",
                "role": "src_host",
                "class": "node",
                "status": 'allow',
                "policy_id": '',
            }
        ]

        for fortigate, value in path.items():
            item = {'name': fortigate.device.name, 'type': 'node', 'ip': fortigate.mgmt_ip,
                    'role': fortigate.role.lower(), 'class': f'node fortigate',
                    'interfaces': [], 'image': "img/fortigate.png", 'status': policies[fortigate]['status']}
            item['interfaces'].append(value['src'][0].zone.name if value['src'][0].zone and not value['src'][0].zone.is_decommissioned else value['src'][0].name)
            item['interfaces'].append(value['dst'][0].zone.name if value['dst'][0].zone and not value['dst'][0].zone.is_decommissioned else value['dst'][0].name)
            # item['interfaces'].append(value['src'][0].name)
            # item['interfaces'].append(value['dst'][0].name)
            if policies[fortigate]['status'] == 'allow':
                policy_id = policies[fortigate]['policies']['allow'][0]
            elif policies[fortigate]['policies']['deny']:
                policy_id = policies[fortigate]['policies']['deny'][0]
            else:
                policy_id = 'Implicit Deny'
            item['policy_id'] = policy_id
            item['fortigate_id'] = fortigate.id
            items.append(item)
        items.append(
            {
                "name": dst,
                "image": "img/host.png",
                "type": "host",
                "ip": f'{protocol.upper()}/{port}' if protocol != 'icmp' else f'{protocol.upper()}/8',
                "role": "dst_host",
                "class": "node",
                "status": 'allow',
                "policy_id": '',
            }
        )
        if data:
            status = draw_topology(items)
            if not status[0]:
                raise Exception(status[1])
            context = status[1]
            context['src'] = src
            context['dst'] = dst
            context['protocol'] = protocol
            context['port'] = port
            context['status'] = 'Success'
            print(context)
            return JsonResponse(context)
    except APIError as err:
        return JsonResponse({'status': 'Failed', 'message': str(err).replace('\n', '<br>')})
    except Error:
        if data:
            logger.info('Invalid Request.\nData:\n{0}'.format(data))
        return HttpResponse(status=400)
    except Exception as err:
        logger.exception(err)
        return HttpResponse(status=500)


def draw_topology(data):
    """
    :param data: [
            {"name": "Host A", "type": "host", "image": "img/host.png"},
            {"name": "Router A", "type": "node", "interfaces": ["A1", "A2"], "image": "img/fortigate.png"},
            {"name": "Router B", "type": "node", "interfaces": ["B1", "B2"], "image": "img/fortigate.png"},
            {"name": "Router C", "type": "node", "interfaces": ["C1", "C2"], "image": "img/fortigate.png"},
            {"name": "Host B", "type": "host", "image": "img/host.png"},
        ]
    :return:
    """
    output = [False, 'Unknown']
    try:
        x_offset = 25
        y_position = 0
        node_spacing = 140  # prev 150
        node_size = 45  # Size of the node images

        # Calculate positions
        positions = []
        for i, item in enumerate(data):
            tmp = {
                'name': item['name'],
                'image': static(item['image']),
                'type': item['type'],
                'role': item['role'],
                'class': item['class'],
                'status': item['status'],
                'policy_id': item['policy_id'],
                'ip': item['ip'],
                'x': x_offset + i * node_spacing,
                'y': y_position,
                #'y2': y_position + node_size / 2 + 5,
                'interfaces': [] if 'interfaces' not in item else item['interfaces']
            }
            if 'fortigate_id' in item:
                tmp['fortigate_id'] = item['fortigate_id']
            positions.append(tmp)

        # Calculate edge lengths and positions
        edges = []
        width = 0

        for i in range(len(data) - 1):
            if positions[i]['type'] == 'host' and positions[i + 1]['type'] == 'node':
                length = len(positions[i + 1]['interfaces'][0])
                if length <= 15:
                    length = length + 10
                    multiplier = 2
                else:
                    multiplier = 8
                new = positions[i + 1]['x'] = positions[i + 1]['x'] + (length / 2 * multiplier)
                """name_length = len(positions[i]['name']) + len(positions[i + 1]['name'])
                if name_length * 8 > new:
                    new = positions[i + 1]['x'] = positions[i + 1]['x'] + (length * 1) + name_length / 2"""
            elif positions[i]['type'] == 'node' and positions[i + 1]['type'] == 'node':
                length = len(positions[i]['interfaces'][1]) + len(positions[i + 1]['interfaces'][0])
                if length <= 15:
                    length = length + 10
                new = positions[i + 1]['x'] = positions[i + 1]['x'] + (length / 2 * 8)  # prev *10
                name_length = len(positions[i]['name']) + len(positions[i + 1]['name'])
                if name_length * 2 > new:  # previously *8
                    new = positions[i + 1]['x'] = positions[i + 1]['x'] + (length / 2 * 8) + name_length / 2  # prev *10
            elif positions[i]['type'] == 'node' and positions[i + 1]['type'] == 'host':
                length = len(positions[i]['interfaces'][1])
                if length <= 15:
                    length = length + 10
                    multiplier = 2
                else:
                    multiplier = 8
                new = positions[i + 1]['x'] = positions[i + 1]['x'] + (length / 2 * multiplier)
                """name_length = len(positions[i]['name']) + len(positions[i + 1]['name'])
                if name_length * 8 > new:
                    new = positions[i + 1]['x'] = positions[i + 1]['x'] + (length * 1) + name_length / 2"""
            x = 1
            for n in range(i + 1):
                try:
                    positions[i + 1 + x]['x'] = new + x * node_spacing
                    x += 1
                except:
                    pass
            edges.append({
                'id': i,
                'x1': positions[i]['x'] + node_size - 2,
                'y1': y_position + node_size / 2,
                'x2': positions[i + 1]['x'] + 2,
                'y2': y_position + node_size / 2,
                'label_y': y_position + node_size / 2 - 5,
                'label1_x': positions[i]['x'] + node_size + 2,
                'label2_x': positions[i + 1]['x'] - 2,
                'length': positions[i + 1]['x'] - positions[i]['x'] - 2 * node_size,
                'label1': '' if not positions[i]['interfaces'] else positions[i]['interfaces'][1],  # Interface labels
                'label2': '' if not positions[i + 1]['interfaces'] else positions[i + 1]['interfaces'][0]
            })
            width = positions[i + 1]['x'] + node_size + x_offset

        context = {
            'items': positions,
            'y_position': y_position,
            'node_size': node_size,
            'edges': edges,
            'width': width,
        }
        output = [True, context]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        return output


def get_interfaces(request):
    fortigate_id = request.GET.get('fortigate_id')
    data = getInterfaces(fortigate_id)
    results = [{'id': item.id, 'text': item.name} for item in data]
    return JsonResponse(results, safe=False)



def get_filtered_fields(request):
    fortigate = request.GET.get('fortigate')
    if fortigate:
        # Filter services based on the fortigate
        services = []
        for item in FortiGateObject.objects.filter(fortigate=fortigate, type__in=['service', 'servicegroup']):
            services.append({'id': item.id, 'name': item.object.name})
        source_address = []
        for item in FortiGateObject.objects.filter(fortigate=fortigate, type__in=['address', 'addressgroup']):
            source_address.append({'id': item.id, 'name': item.object.name})
        destination_address = []
        for item in FortiGateObject.objects.filter(fortigate=fortigate, type__in=['address', 'addressgroup', 'vip', 'vipgroup']):
            destination_address.append({'id': item.id, 'name': item.object.name})

        # Return the filtered results as JSON
        return JsonResponse({
            'services': list(services),
            'source_address': list(source_address),
            'destination_address': list(destination_address),
        })
    return JsonResponse({
        'services': [],
        'source_address': [],
        'destination_address': []
    })


def track_submission(request, src, dst, protocol, port, user_group):
    """Track submission count using session storage."""
    empty = False
    if "submission_counts" not in request.session:
        request.session["submission_counts"] = {}
        empty = True
    input_key = f"{src}|{dst}|{protocol}|{port}|{user_group}"
    submission_counts = request.session["submission_counts"]
    if submission_counts and input_key not in submission_counts:
        submission_counts = {}
    logger.info(submission_counts)
    submission_counts[input_key] = submission_counts.get(input_key, 0) + 1
    if submission_counts[input_key] > 5:
        submission_counts[input_key] = 0

    request.session["submission_counts"] = submission_counts
    request.session.modified = True

    return submission_counts[input_key]


class PolicyView(PermissionRequiredMixin, View):
    permission_required = (
        "dcim.view_device",
        "netbox_fortigate.view_fortigatepolicy"
    ) 

    def get(self, request, fortigate=None, pid=None, *args, **kwargs):
        context = {}
        error = None

        try:
            if fortigate and pid:
                fg = FortiGateDevice.objects.filter(id=fortigate).first()
                if fg:
                    obj = (
                        FortiGatePolicy.objects.filter(
                            fortigate=fg,
                            is_decommissioned=False,
                            policyid=pid,
                        )
                        .first()
                    )

                    if obj:
                        policy = {}
                        users = []

                        policy["Device"] = obj.fortigate.device.name
                        policy["ID"] = obj.id
                        policy["PID"] = obj.policyid
                        policy["Policy Name"] = obj.name or ""
                        policy["Source"] = get_objects_values(obj.source_address.all(), True)
                        policy["Destination"] = get_objects_values(obj.destination_address.all(), True)
                        policy["Schedule"] = get_objects_values([obj.schedule], True)
                        policy["Service"] = get_objects_values(obj.service.all(), True)
                        policy["Action"] = (obj.action or "").upper()

                        if obj.expiry_date:
                            policy["Expiration Date"] = timezone.localtime(obj.expiry_date).strftime(
                                "%B %d, %Y %H:%M"
                            )

                        if obj.users.all():
                            users.extend(get_objects_values(obj.users.all(), False, "User"))
                        if obj.groups.all():
                            users.extend(get_objects_values(obj.groups.all(), False, "UserGroup"))

                        if users:
                            policy["Users"] = ", ".join(users)

                        context["policy"] = policy
                    else:
                        error = f"Local DB has no record yet for Policy ID {pid} of {str(fg)}"
                else:
                    error = "Device does not exist."
        except Exception as err:
            logger.exception(err)
            error = str(err)

        if error:
            context["error"] = error

        return render(request, "netbox_fortigate/policy.html", context=context)
    

@csrf_exempt
def policy_view(request, fortigate=None, pid=None):
    context = {}
    error = None
    try:
        if fortigate and pid:
            fortigate = FortiGateDevice.objects.filter(id=fortigate).first()
            if fortigate:
                obj = FortiGatePolicy.objects.filter(fortigate=fortigate, is_decommissioned=False, policyid=pid).first()
                policy = {}
                users = []
                if obj:
                    policy['Device'] = obj.fortigate.device.name
                    policy['ID'] = obj.id
                    policy['PID'] = obj.policyid
                    policy['Policy Name'] = obj.name if obj.name else ''
                    policy['Source'] = get_objects_values(obj.source_address.all(), True)
                    policy['Destination'] = get_objects_values(obj.destination_address.all(), True)
                    policy['Schedule'] = get_objects_values([obj.schedule], True)
                    policy['Service'] = get_objects_values(obj.service.all(), True)
                    policy['Action'] = obj.action.upper()
                    if obj.expiry_date:
                        policy['Expiration Date'] = timezone.localtime(obj.expiry_date).strftime("%B %d, %Y %H:%M")
                    if obj.users.all():
                        users.extend(get_objects_values(obj.users.all(), False, 'User'))
                    if obj.groups.all():
                        users.extend(get_objects_values(obj.groups.all(), False, 'UserGroup'))
                    if users:
                        policy['Users'] = ', '.join(users)
                    context['policy'] = policy
                else:
                    error = f"Local DB has no record yet for Policy ID {pid} of {str(fortigate)}"
            else:
                error= "Device does not exist."
    except Exception as err:
        logger.exception(err)
        error = str(err)
    if error:
        context['error'] = error
    return render(request, 'netbox_fortigate/policy.html', context=context)


