from netbox.plugins import PluginConfig


class NetBoxFortigateConfig(PluginConfig):
    name = "netbox_fortigate"
    verbose_name = "FortiGate"
    description = "FortiGate policy workflow and automation for NetBox"
    version = "0.1.0"
    base_url = "fortigate"
    min_version = "4.1.3"
    max_version = "4.5.1"

    def ready(self):
        super().ready()

        from core.models import ObjectType
        from .models import FortiGateScheduler 
        from . import signals # noqa
        
        ot = ObjectType.objects.get_for_model(FortiGateScheduler, for_concrete_model=False)
        if "jobs" not in ot.features:
            ot.features = list({*ot.features, "jobs"})
            ot.save(update_fields=["features"])


        
config = NetBoxFortigateConfig
