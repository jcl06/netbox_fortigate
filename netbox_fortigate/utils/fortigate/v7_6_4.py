import sys
import json
import requests

from .base import FORTIGATE


class FTGv764(FORTIGATE):
    """
    For FortiOS v7.6.4
    """

    def login_url(self, ip=None):
        return f"https://{ip or self.ip}:{self.port}/api/v2/authentication"

    def login_payload(self):
        return json.dumps({
            "username": self.user,
            "password": self.password
        })
        
    def logout(self):
        output = [False, 'Unknown']
        try:
            if self.session:
                self.logger.info('Logging out')
                url = f"https://{self.ip}:{self.port}/api/v2/authentication"
                try:
                    response = self.session.delete(url, verify=False, timeout=10)
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
        
