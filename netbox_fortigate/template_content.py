from netbox.plugins import PluginTemplateExtension

class FortigateButtons(PluginTemplateExtension):
    models = ("dcim.device",)

    def buttons(self):
        device = self.context["object"]

        # Decide when to show the button. Example: platform contains "forti"
        is_fortigate = bool(device.device_type and "fortigate" in name.lower() for name in [device.device_type.slug, device.device_type.model])

        if not is_fortigate:
            return ""

        return self.render("netbox_fortigate/inc/device_pull_inventory_button.html")


template_extensions = [FortigateButtons]