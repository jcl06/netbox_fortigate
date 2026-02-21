from netaddr import AddrFormatError, IPAddress

from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from ipam.fields import BaseIPField
from ipam.formfields import IPAddressFormField

class HostAddressField(BaseIPField):
    """
    IP address (IP address without mask).
    Uses PostgreSQL 'inet' field type.
    """

    description = _("PostgreSQL INET field")

    form_class = IPAddressFormField

    def db_type(self, connection):
        return 'inet'
    
    def to_python(self, value):
        """Converts the input value into an IPAddress object."""
        if not value:
            return None
        try:
            return IPAddress(value)
        except AddrFormatError:
            raise ValidationError(_("Invalid IP address format: {address}").format(address=value))
        except (TypeError, ValueError) as e:
            raise ValidationError(str(e))

    def get_prep_value(self, value):
        """Prepares the value for database storage."""
        if not value:
            return None
        return str(IPAddress(value))