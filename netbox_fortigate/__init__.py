from netbox.plugins import PluginConfig


class NetBoxFortigateConfig(PluginConfig):
    name = "netbox_fortigate"
    verbose_name = "FortiGate"
    description = "FortiGate policy workflow and automation for NetBox"
    version = "0.1.0"
    base_url = "fortigate"
    min_version = "4.1.3"
    max_version = "4.1.3"


config = NetBoxFortigateConfig
