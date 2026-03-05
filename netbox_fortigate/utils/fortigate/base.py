import requests
import urllib3
import time
import json
import logging
from django.utils import timezone
import datetime
from ..validators import validate_IPv4Address


__all__ = (
    'FORTIGATE',
)


class FORTIGATE:
    def __init__(self, data=None, debug=False, vdom='root', port=443, timeout=900):
        # data={'username':'', 'password':'', 'ip':''}
        self.user = ''
        self.password = ''
        self.ip = ''
        self.timeout = timeout  # in seconds
        self.token = ''
        self.tokenstarttime = 0
        self.version = None
        '''
            self.tokenRenewalPeriod = 120
            If time remaining is less than or equal 120 seconds renew the token. 
            Need to convert into dynamic/constant variable from DB or config file
        '''
        self.tokenRenewalPeriod = 120
        self.logger = logging.getLogger('FORTIGATE')
        self.starttime = timezone.localtime()
        self.ERROR = False
        self.session = None
        self.IPs = []
        self.DEBUG = debug
        self.vdom = vdom
        self.port = port
        self.interfaces = {}
        self.zones = {}
        self.addresses = {}
        self.address_groups = {}
        self.services = {}
        self.service_groups = {}
        self.profile_groups = {}
        self.ippools = {}
        self.ipv4_routes = {}
        self.ipv6_routes = {}
        self.policies = {}
        self.routing_policies = {}
        self.vdoms = []
        self.schedule_onetime = {}
        self.schedule_recurring = {}
        self.schedule_groups = {}
        self.users = {}
        self.user_groups = {}
        self.authentication_servers = {}
        self.vip = {}
        self.vip_groups = {}
        self.hostname = ""

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if data:
            setData = self.set_data(data)
            if not setData[0]:
                self.ERROR = setData[1]

    def set_data(self, data):
        output = [False, 'Unknown']
        try:
            self.logger.info('Initialize Data')
            if 'username' in data and 'password' in data:
                if not data['username'] or not data['password']:
                    raise Exception('No Username/Password provided.')
                self.user = data['username']
                self.password = data['password']
            if 'vdom' in data:
                self.vdom = data['vdom']
            if 'ip' in data:
                self.ip = data['ip']
            else:
                raise Exception('No IP provided.')
            if 'device' in data and data['device']:
                self.hostname = data['device']
            if 'port' in data:
                self.port = data['port']
            if 'timeout' in data:
                self.timeout = data['timeout']
            if not self.session:
                status = self.get_session()
                if not status[0]:
                    raise Exception(status[1])
            output = [True, 'Successful']
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_session(self, ip=''):
        output = [False, 'Unknown']
        token = ''
        try:
            ip_addr = ip or self.ip
            status = self.login(ip_addr)
            if status[0]:
                self.ip = ip_addr
            if not self.session:
                raise Exception(f'Unable to connect from any of the {ip_addr} provided.')
            output = [True, token]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def login_url(self, ip=None):
        return f"https://{ip or self.ip}:{self.port}/logincheck"

    def login_payload(self):
        return f"username={self.user}&secretkey={self.password}"

    def login(self, ip=''):
        output = [False, 'Unknown']
        try:
            if not ip:
                if self.ip:
                    ip = self.ip
                else:
                    raise Exception('Unable to login. No IP provided.')
            self.logger.info('Login to {0}'.format(ip))
            url = self.login_url(ip)
            self.session = requests.session()
            payload = self.login_payload()
            headers = {
                'Content-Type': 'application/json',
            }
            try:
                response = self.session.request('POST', url, data=payload, headers=headers, verify=False, timeout=10)
            except requests.exceptions.ConnectionError as e:
                self.logger.error(e)
                err = 'Connection Error: Please ensure IP address ({0}) is correct or reachable.'.format(ip)
                raise Exception(err)

            if response.status_code != 200:
                self.logger.debug('Response: {0}'.format(response.text))
                raise Exception('{0} Unable to connect!'.format(self.ip))
            else:
                self.logger.info('Session Validation')
                uri = f'https://{self.ip}:{self.port}/api/v2/monitor/system/status'
                try:
                    r = self.session.request('GET', uri, headers=headers, verify=False)
                except requests.exceptions.ConnectionError as e:
                    self.logger.error(e)
                    err = 'Connection Error: Please ensure the url ({0}) is correct or reachable.'.format(uri)
                    raise Exception(err)
                if r.status_code != 200:
                    self.logger.info('Session validation failed!')
                    self.logger.debug('Response: {0}'.format(r.text))
                    raise Exception('{0} Session Validation failed'.format(self.ip))
                self.logger.info('Session validation successful.')
                self.logger.debug({'Data': r.json()})
                data = r.json()
                if 'vdom' not in data:
                    self.logger.info('"vdom" key not found')
                    self.logger.debug('data: \n\n{0}\n'.format(data))
                    raise Exception('vdom key not found')
                if self.vdom != data['vdom']:
                    self.logger.warning(f'vdom does not matched. {data['vdom']}:{self.vdom} (device:DB)')
                    self.logger.info(f'vdom has set from "{self.vdom}" to "{data['vdom']}"')
                    self.vdom = data['vdom']
                if 'version' in data:
                    self.version = data['version']
                hostname = data.get('results', {}).get('hostname')
                if hostname and hostname != self.hostname:
                    self.hostname = hostname
            self.tokenstarttime = time.time()
            output = [True, 'Successfully login to {0}'.format(self.ip)]
            self.logger.info('Successfully login to {0}'.format(self.ip))
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def check_session_validity(self):
        output = [False, 'Unknown']
        try:
            self.logger.debug('Check Session Validity.')
            if not self.session:
                login = self.login()
                if not login[0]:
                    raise Exception(login[1])
            remain_time = self.timeout - (time.time() - self.tokenstarttime)
            if remain_time <= 0:
                self.logger.info('Session expired has expired for {0} seconds.'.format(remain_time*-1))
                login = self.login()
                if not login[0]:
                    raise Exception(login[1])
                msg = login[1]
            elif remain_time <= self.tokenRenewalPeriod:
                self.logger.info('Session has less then {0} seconds.'.format(self.tokenRenewalPeriod))
                renew = self.renew_session()
                if not renew[0]:
                    raise Exception(renew[1])
                msg = renew[1]
            else:
                msg = 'Session still valid with for {0} seconds.'.format(remain_time)
                self.logger.debug(msg)
            output = [True, msg]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def renew_session(self):
        output = [False, 'Unknown']
        try:
            self.logger.info('Renewing session.')
            if not self.session:
                login = self.login()
                if not login[0]:
                    raise Exception(login[1])
            status = self.api_request('monitor/system/status', session_refresh=True)
            if not status[0]:
                raise Exception(status[1])
            self.tokenstarttime = time.time()
            output = [True, 'Successfuly refresh API session.']
            self.logger.info('Successfuly refresh API session.')
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def api_request(self, uri, method="GET", payload=None, session_refresh=False, params={}):
        output = [False, 'Unknown']
        try:
            self.logger.info('Sending {0} API request ({1})'.format(method, uri))
            if not self.session:
                login = self.login()
                if not login[0]:
                    raise Exception(login[1])
            else:
                if not session_refresh:
                    status = self.check_session_validity()
                    if not status[0]:
                        raise Exception(status[1])
            uri = uri.strip('/')
            url = f'https://{self.ip}:{self.port}/api/v2/{uri}?vdom={self.vdom}'
            self.logger.debug('URI: {0}'.format(url))

            try:
                if payload:
                    self.logger.debug('Payload: \n{0}\n'.format(payload))
                    response = self.session.request(method, url, data=json.dumps(payload), verify=False, timeout=(10, 600)) # 10s to connect, 10 minutes for response
                elif params:
                    self.logger.debug('Parameters: \n{0}\n'.format(params))
                    response = self.session.request(method, url, params=params, verify=False)
                else:
                    response = self.session.request(method, url, verify=False)
            except requests.exceptions.ConnectionError as e:
                self.logger.error(e)
                err = 'Connection Error: Please ensure API URL ({0}) is correct.'.format(url)
                raise Exception(err)

            if response.status_code == 200:
                self.logger.debug({
                    'Response': response.status_code,
                    'Type': response.headers.get('content-type'),
                    'Data': response.json()
                })

                data = response.json()
                if 'results' not in data:
                    self.logger.info('"results" key not found')
                    self.logger.info(data)
                    raise Exception('Results not found')
                output = [True, data['results'], data]
            else:
                self.logger.info("API Response: {0}-{1}".format(response.status_code, response.text))
                raise Exception("{0}-{1}".format(response.status_code, response.text))
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def logout(self):
        output = [False, 'Unknown']
        try:
            if self.session:
                self.logger.info('Logging out')
                url = f'https://{self.ip}:{self.port}/logout'
                try:
                    response = self.session.request('POST', url, verify=False)
                except requests.exceptions.ConnectionError as e:
                    self.logger.error(e)
                    err = 'Connection Error: Please ensure API URL ({0}) is correct.'.format(url)
                    raise Exception(err)
                if response.status_code != 200:
                    self.logger.info('Logout unsuccessful')
                    self.logger.info('HTTP Response: {0}'.format(response.status_code))
                    self.logger.debug("Response Content {0}-{1}".format(response.status_code, response.text))
                    raise Exception('Unable to logout')
            else:
                raise Exception('No existing session found')
            output = [True, 'Logout successful', response]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def close_session(self):
        if self.session:
            self.logout()
            self.session.close()
            self.session = None

    def get_interfaces(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('cmdb/system/interface')
            if not status[0]:
                raise Exception(status[1])
            interfaces = {
                'Null': {
                    'name': 'Null',
                    'ip': '',
                    'status': 'down',
                    'type': '',
                    'description': 'Added by the system by default',
                    'role': '',
                    'vdom': self.vdom,
                    'enabled': True,
                    'parent': ''
                },
                'any': {
                    'name': 'any',
                    'ip': '',
                    'status': 'down',
                    'type': '',
                    'description': 'Added by the system by default',
                    'role': '',
                    'vdom': self.vdom,
                    'enabled': True,
                    'parent': ''
                },
                self.vdom: {
                    'name': self.vdom,
                    'ip': '',
                    'status': 'down',
                    'type': '',
                    'description': 'Added by the system by default',
                    'role': '',
                    'vdom': self.vdom,
                    'enabled': True,
                    'parent': ''
                }
            }
            interfaces_with_parent = {}

            interface_with_errors = []
            for item in status[1]:
                if item['type'] in ['vdom-link']:
                    msg = f'Skipping {item["type"]} type interface ({item["name"]})'
                    self.logger.info(msg)
                    interface_with_errors.append([item['name'], msg])
                    continue
                if item['vdom'] == self.vdom:
                    status = validate_IPv4Address(item['ip'])
                    if not status[0]:
                        self.logger.info(status[1])
                        self.logger.error(f'Unable to add interface "{item["name"]}" due to {status[1]}')
                        self.logger.debug(f'data: \n{item}')
                        interface_with_errors.append([item['name'], status[1]])
                        continue
                    ip = status[1]
                    interface = {
                        'name': item['name'],
                        'ip': '' if '0.0.0.0' in ip else ip,
                        'status': item['status'],
                        'type': item['type'],
                        #'member': [m['interface-name'] for m in item['member']] if item['member'] else [],
                        'description': item['description'] or item['alias'],
                        'role': '' if item['role'] == 'undefined' else item['role'],
                        'vdom': item['vdom'],
                        'enabled': True if item['status'] == 'up' else False,
                        'parent': item['aggregate'] if 'aggregate' in item else item['interface'] if item['type'] == 'tunnel' and item['interface'] else ''
                    }
                    if 'aggregate' in item or (item['type'] == 'tunnel' and item['interface']):
                        interfaces_with_parent[item['name']] = interface
                    else:
                        interfaces[item['name']] = interface
            self.interfaces = {**interfaces, **interfaces_with_parent}
            output = [True, interfaces, interface_with_errors]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_vdoms(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request(f'cmdb/system/vdom')
            if not status[0]:
                raise Exception(status[1])
            self.vdoms = vdoms = [item['name'] for item in status[1]]
            output = [True, vdoms]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_zones(self, zone=''):
        output = [False, 'Unknown']
        try:
            status = self.api_request(f'cmdb/system/zone/{zone}')
            if not status[0]:
                raise Exception(status[1])
            zones = {}
            for item in status[1]:
                zones[item['name']] = {
                    'name': item['name'],
                    'description': item['description'],
                    'intrazone': item['intrazone'],
                    'type': 'normal',
                    'interface': [i['interface-name'] for i in item['interface']] if item['interface'] else []
                }
            if not zone:
                self.zones = zones
                self.get_sdwan_zones()
            else:
                zones = zones[zone]
            output = [True, zones]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_sdwan_zones(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request(f'cmdb/system/sdwan')
            if not status[0]:
                raise Exception(status[1])
            zones = {}
            for item in status[1]['zone']:
                zones[item['name']] = {
                    'name': item['name'],
                    'description': '' if 'description' not in item else item['description'],
                    'intrazone': 'deny' if 'intrazone' not in item else item['intrazone'],
                    'type': 'sdwan',
                    'interface': []
                }
            for item in status[1]['members']:
                if item['interface'] not in zones[item['zone']]['interface']:
                    zones[item['zone']]['interface'].append(item['interface'])
            
            self.zones.update(zones)
            output = [True, self.zones]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_routing_table(self, version=4):
        output = [False, 'Unknown']
        try:
            status = self.api_request(f'monitor/router/ipv{version}')
            if not status[0]:
                raise Exception(status[1])
            routes = {}
            for item in status[1]:
                route = {
                    'type': item['type'],
                    'gateway': '' if item['gateway'] == '0.0.0.0' or item['gateway'] == '::' else item['gateway'],
                    'interface': item['interface'],
                    'distance': item['distance'],
                    'priority': item['priority'],
                    'metric': item['metric'],
                }
                if 'is_tunnel_route' in item:
                    if item['is_tunnel_route']:
                        status = self.api_request(f'cmdb/system/interface/{item['interface']}')
                        if not status[0]:
                            self.logger.warning(f'Unable to add {item['ip_mask']} due to {status[1]}')
                            continue
                        gw = status[1][0]['remote-ip'].split(' ')[0]
                        if gw != '0.0.0.0':
                            route['gateway'] = gw
                        else:
                            route['gateway'] = '' if item['gateway'] == '0.0.0.0' else item['gateway']

                if item['ip_mask'] not in routes:
                    routes[item['ip_mask']] = [route]
                else:
                    routes[item['ip_mask']].append(route)

            if version == 4:
                self.ipv4_routes = routes
            else:
                self.ipv6_routes = routes
            output = [True, routes]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def policy_lookup(self, *option, **options):
        """
        To check if has existing firewall policy on the device
        :param options: {}
            ipv6: bool
            srcintf*: string
            sourceip: string
            protocol*: string # tcp, udp, protocol number: ex. tcp(6), udp(17), icmp(1)
            dest*: string # Destination IP or FQDN
            destport: integer
            icmptype: integer
            icmpcode: integer
        :return: return policy_id number if it has policy matched else 0
        """
        output = [False, 'Unknown']
        action = 'deny'
        try:
            if not options and not option:
                raise Exception('No options provided')
            if len(option) > 1:
                raise Exception('Input is in invalid format')
            if option:
                if not isinstance(option[0], dict):
                    raise Exception('Input is in invalid format')
                options = option[0]
            for k, v in options.items():
                if isinstance(v, bool):
                    options[k] = str(v).lower()
            status = self.api_request(f'monitor/firewall/policy-lookup', params=options)
            if not status[0]:
                raise Exception(status[1])
            data = status[1]
            if 'success' not in data:
                self.logger.info('"success" key not found')
                self.logger.info(data)
                raise Exception('Key "success" not found')
            if data['success']:
                policy_id = data['policy_id']
                if policy_id:
                    if not self.policies:
                        status = self.get_policies(policy=policy_id)
                        if not status[0]:
                            raise Exception(status[1])
                        action = status[1]['action']
                    else:
                        action = self.policies[policy_id]['action']
                output = [True, policy_id, action]
            elif data['success'] == False:
                if 'error_code' in data:
                    action = data['error_code']
                else:
                    action = data
                output = [False, action]
            else:
                output = [True, 0, action]  # 0 Means no policy found on the device
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_policies(self, policy=''):
        output = [False, 'Unknown']
        try:
            status = self.api_request(f'cmdb/firewall/policy/{policy}')
            if not status[0]:
                raise Exception(status[1])
            policies = {}
            position = 0
            for item in status[1]:
                # if item['name'] or policy:
                position = position + 1
                policies[item['policyid']] = {
                    'policyid': item['policyid'],
                    'name': item['name'],
                    'status': item['status'],
                    'source_interface': [i['name'] for i in item['srcintf']] if item['srcintf'] else [],
                    'destination_interface': [i['name'] for i in item['dstintf']] if item['dstintf'] else [],
                    'action': item['action'],
                    #'nat64': item['nat64'] if 'nat64' in item else '',  # this key is not supported by version below 7
                    #'nat46': item['nat46'] if 'nat46' in item else '',  # this key is not supported by version below 7
                    'source_address': [i['name'] for i in item['srcaddr']] if item['srcaddr'] else [],
                    'destination_address': [i['name'] for i in item['dstaddr']] if item['dstaddr'] else [],
                    'schedule': item['schedule'],
                    'service': [i['name'] for i in item['service']] if item['service'] else [],
                    #'utm-status': item['utm-status'],
                    'inspection_mode': item['inspection-mode'],
                    'profile_type': item['profile-type'],
                    'profile_group': item['profile-group'],
                    'logging': item['logtraffic'],
                    'nat': item['nat'],

                    'groups': [i['name'] for i in item['groups']] if item['groups'] else [],
                    'users': [i['name'] for i in item['users']] if item['users'] else [],
                    'expiry': item['policy-expiry'] if 'policy-expiry' in item else 'disable',
                    'expiry_date': datetime.datetime.strptime(
                        item['policy-expiry-date'], "%Y-%m-%d %H:%M:%S"
                    ).strftime("%H:%M %Y/%m/%d") if 'policy-expiry-date' in item and item['policy-expiry-date'] else None,
                    'comments': item['comments'],
                    'position': position
                }
            if not policy:
                self.policies = policies
            else:
                policies = policies[policy]
            output = [True, policies]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_address_objects(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall/address/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'type': item['type'],
                    'subnet': validate_IPv4Address(item['subnet'])[1] if 'subnet' in item else '',
                    'start_ip': item['start-ip'] if 'start-ip' in item else '',
                    'end_ip': item['end-ip'] if 'end-ip' in item else '',
                    'fqdn': item['fqdn'] if 'fqdn' in item else '',
                    'interface': item['interface'],
                    'comment': item['comment'],
                }
            self.addresses = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_address_groups(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall/addrgrp/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'type': item['type'],
                    'member': [i['name'] for i in item['member']] if item['member'] else [],
                    'comment': item['comment'],
                }
            self.address_groups = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def get_schedule_onetime(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall.schedule/onetime/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'start': item['start'],
                    'end': item['end']
                }
            self.schedule_onetime = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output

    def get_schedule_recurring(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall.schedule/recurring/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'start': item['start'],
                    'end': item['end'],
                    'day': item['day']
                }
            self.schedule_recurring = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def get_schedule_groups(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall.schedule/group/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'member': [i['name'] for i in item['member']] if item['member'] else [],
                }
            self.schedule_groups = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def get_services(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall.service/custom/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'protocol': item['protocol'],
                    'protocol_number': item['protocol-number'] if 'protocol-number' in item and not item['protocol-number'] is None else None,
                    'icmptype': item['icmptype'] if 'icmptype' in item and item['icmptype'] else None,
                    'tcp_portrange': item['tcp-portrange'] if 'tcp-portrange' in item else '',
                    'udp_portrange': item['udp-portrange'] if 'udp-portrange' in item else '',
                    'comment': item['comment'],
                }
            self.services = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def get_service_groups(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall.service/group/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'member': [i['name'] for i in item['member']] if item['member'] else [],
                    'comment': item['comment'],
                }
            self.service_groups = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
            output = [False, err]
        finally:
            return output
        
    def get_profile_groups(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall/profile-group/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name']
                }
            self.profile_groups = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def get_ippools(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall/ippool/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'type': item['type'],
                    'startip': item['startip'],
                    'endip': item['endip'],
                    'startport': item['startport'],
                    'endport': item['endport'],
                    'source_startip': item['source-startip'],
                    'source_endip': item['source-endip'],
                    'block_size': item['block-size'],
                    'num_blocks_per_user': item['num-blocks-per-user'],
                    'arp_reply': item['arp-reply'],
                    'comments': item['comments'],
                }
            self.ippools = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def get_users(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/user/local/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                if item['ldap-server']:
                    server = item['ldap-server']
                elif item['radius-server']:
                    server = item['radius-server']
                elif item['tacacs+-server']:
                    server = item['tacacs+-server']
                else:
                    server = ''
                objects[item['name']] = {
                    'name': item['name'],
                    'type': item['type'],
                    'status': item['status'],
                    'server': server
                }
            self.users = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
            output = [False, err]
        finally:
            return output
        
    def get_user_groups(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/user/group/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'member': [i['name'] for i in item['member']] if item['member'] else [],
                    'match': [{'server_name': i['server-name'], 'group_name': i['group-name']} for i in item['match']] if item['match'] else {}
                }
            self.user_groups = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
            output = [False, err]
        finally:
            return output
        
    
    def get_vip(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall/vip/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'type': item['type'],
                    'src_filter': [i['range'] for i in item['src-filter']] if item['src-filter'] else [],
                    'service': [i['name'] for i in item['service']] if item['service'] else [],
                    'external_ip': item['extip'],
                    'external_address': item['extaddr'][0]['name'] if item['extaddr'] else '',
                    'mapped_ip': item['mappedip'][0]['range'] if item['mappedip'] else '',
                    'mapped_address': item['mapped-addr'],
                    'external_interface': item['extintf'],
                    'port_forward': item['portforward'],
                    'status': item['status'],
                    'protocol': item['protocol'],
                    'external_port': item['extport'],
                    'mapped_port': item['mappedport'],
                    'portmapping_type': item['portmapping-type'],
                    'comment': item['comment'],
                }
            self.vip = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
            output = [False, err]
        finally:
            return output
            
    def get_vip_groups(self):
        output = [False, 'Unknown']
        try:
            status = self.api_request('/cmdb/firewall/vipgrp/')
            if not status[0]:
                raise Exception(status[1])
            objects = {}
            for item in status[1]:
                objects[item['name']] = {
                    'name': item['name'],
                    'interface': item['interface'],
                    'member': [i['name'] for i in item['member']] if item['member'] else [],
                    'comments': item['comments']
                }
            self.vip_groups = objects
            output = [True, objects]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output
        
    def get_authentication_servers(self):
        output = [False, 'Unknown']
        types = ['radius', 'tacacs+', 'ldap', 'saml']
        try:
            for type in types:
                status = self.api_request(f'cmdb/user/{type}/')
                if not status[0]:
                    raise Exception(status[1])
                objects = {}
                for item in status[1]:
                    objects[item['name']] = {
                        'name': item['name'],
                        'type': type,
                        'server': item['server'] if 'server' in item else ''
                    }
                self.authentication_servers.update(objects)
            output = [True, self.authentication_servers]
        except Exception as err:
            self.logger.exception(err)
            output = [False, str(err)]
        finally:
            return output