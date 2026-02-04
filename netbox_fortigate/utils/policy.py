import logging

from django.conf import settings
from .fortigate import FORTIGATE
from .settings import get_plugin_default

__all__ = (
    'find_policy',
)

logger = logging.getLogger(__name__)




def find_policy(device_ip, srcintf, src, dst, protocol=1, port=0, auth_type=None, user_group=None, icmptype=None, device=None):
    """
    :param device_ip:
    :param srcintf:
    :param src:
    :param dst:
    :param protocol: 1 = ICMP, 6 = TCP, 17 = UDP
    :param port:
    :param icmptype: 8 for Ping Echo request, 0 for Ping Echo reply
    :param auth_type: user or group
    :param user_group: Name of local user or login id
    :return:
    """
    output = [False, 'Unknown']
    fortigate = None
    try:
        data = {
            'ip': device_ip,
            'username': get_plugin_default('fortigates_username'),
            'password': get_plugin_default('fortigates_password'),
            'port': get_plugin_default("default_api_port", 443) or 443,
            'device': device
        }
        fortigate = FORTIGATE(data, debug=settings.DEBUG)
        if fortigate.ERROR:
            raise Exception(fortigate.ERROR)
        options = {
            "srcintf": srcintf,
            "sourceip": src,
            "dest": dst,
            "protocol": protocol,
            "destport": port,
        }
        if auth_type and user_group:
            options['auth_type'] = auth_type
            options['user_group'] = user_group
            options['policy_type'] = 'policy'
        if icmptype is not None:
            options['icmptype'] = icmptype
        status = fortigate.policy_lookup(**options)
        if not status[0]:
            raise Exception(status[1])
        output = [True, status[1], status[2]]
    except Exception as err:
        logger.exception(err)
        output = [False, str(err)]
    finally:
        if fortigate:
            fortigate.close_session()
        return output
