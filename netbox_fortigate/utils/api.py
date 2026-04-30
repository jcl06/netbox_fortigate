from .fortigate import *

class APILoader:
    """
    Dynamically resolves the FortiGate API class based on the version string.
    """
    def get(self, version, default=None):
        if not version:
            return default
        
        # Remove leading 'v' and split into parts
        # e.g. "v7.6.4" -> [7, 6, 4]
        v_str = version.lstrip('v')
        try:
            # Handle versions with non-numeric parts if any (like 7.2.0-p1)
            # but usually they are just numbers
            v_parts = [int(p) for p in v_str.split('.') if p.isdigit()]
        except (ValueError, AttributeError):
            return default

        if not v_parts:
            return default

        # Logic: 7.6.4 and all subsequent versions use FTGv764
        if v_parts >= [7, 6, 4]:
            return FTGv764
        
        # Logic: Everything from 7.0.0 up to 7.6.3 uses FTGv7
        if v_parts >= [7, 0, 0]:
            return FTGv7
            
        return default

# Replace the static dictionary with our dynamic loader
# This maintains backward compatibility with API.get(version) calls
API = APILoader()