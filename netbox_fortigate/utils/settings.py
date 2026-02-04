from django.conf import settings

    
def get_plugin_default(key: str, fallback=None):
    cfg = getattr(settings, "PLUGINS_CONFIG", {}) or {}
    plugin_cfg = cfg.get("netbox_fortigate", {}) or {}
    value = plugin_cfg.get(key, None)
    return value if value is not None else fallback