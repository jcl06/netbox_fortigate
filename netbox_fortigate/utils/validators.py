import ipaddress


def validate_IPv4Address(ip_address):
    output = [False, 'Unknown']
    try:
        if ' ' in ip_address:
            ip, mask = ip_address.split()
        else:
            ip, mask = ip_address.split('/')
        if not _is_valid_subnet_mask(mask):
            raise Exception(f'{mask} is not a valid mask.')
        ip_address = f'{ip}/{mask}'
        try:
            prefixlen = ipaddress.ip_network(ip_address, strict=False).prefixlen
        except Exception as err:
            raise Exception(err)
        output = [True, f'{ip}/{prefixlen}']
    except Exception as err:
        output = [False, str(err)]
    finally:
        return output


def _is_valid_subnet_mask(mask):
    if "." in mask:
        parts = mask.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
    else:
        if not mask.isdigit():
            return False
        num = int(mask)
        if num < 0 or num > 255:
            return False
    return True
