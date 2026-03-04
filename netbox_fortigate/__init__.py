from netbox.plugins import PluginConfig

class NetBoxFortigateConfig(PluginConfig):
    name = "netbox_fortigate"
    verbose_name = "Fortigate"
    description = "Fortigate policy workflow and automation for NetBox"
    version = "0.1.0"
    base_url = "fortigate"
    min_version = "4.1.3"
    max_version = "4.5.1"

    def ready(self):
        super().ready()

        from core.models import ObjectType
        from .models import Scheduler, Fortigate
        from utilities.views import register_model_view
        from dcim.models import Device
        from netbox_fortigate.views.device_tabs import DeviceJobsTabView
        from . import signals, logging # noqa
        from . import event_rules
    

        # Ensure ObjectType.features includes "jobs" (DB-backed)
        for model in (Fortigate, Scheduler):
            ot = ObjectType.objects.get_for_model(model, for_concrete_model=False)
            if "jobs" not in ot.features:
                ot.features = list({*ot.features, "jobs"})
                ot.save(update_fields=["features"])
            
        register_model_view(Device, name="fortigate", path="fortigate")(DeviceJobsTabView)

        from .navigation import update_menu
        update_menu()

        
config = NetBoxFortigateConfig
