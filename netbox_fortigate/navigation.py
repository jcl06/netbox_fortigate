from django.utils.translation import gettext as _

from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem


menu_items = (
    PluginMenuItem(
        link="plugins:netbox_fortigate:fortigatedevice_list",
        link_text=_("Firewalls"),
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_fortigate:fortigatedevice_add",
                title=_("Add FortiGate device"),
                icon_class="mdi mdi-plus-thick",
            ),
            PluginMenuButton(
                link="plugins:netbox_fortigate:fortigatedevice_import",
                title=_("Import FortiGate device"),
                icon_class='mdi mdi-upload',
            ),
        ),
    ),
     PluginMenuItem(
        link="plugins:netbox_fortigate:fortigateinterface_list",
        link_text=_("Interfaces"),
        # buttons=(
        #     PluginMenuButton(
        #         link="plugins:netbox_fortigate:fortigateinterface_add",
        #         title=_("Add interface"),
        #         icon_class="mdi mdi-plus-thick",
        #     ),
        # ),
    ),
    PluginMenuItem(
        link="plugins:netbox_fortigate:fortigatezone_list",
        link_text=_("Zones"),
        # buttons=(
        #     PluginMenuButton(
        #         link="plugins:netbox_fortigate:fortigatezone_add",
        #         title=_("Add zone"),
        #         icon_class="mdi mdi-plus-thick",
        #     ),
        # ),
    ),
    PluginMenuItem(
        link="plugins:netbox_fortigate:fortigateroute_list",
        link_text=_("Routing Table"),
    ),
)

request_menu_items = (
    PluginMenuItem(
        link="plugins:netbox_fortigate:requests",
        link_text=_("My Requests"),
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_fortigate:requests",
                title=_("Open"),
                icon_class="mdi mdi-open-in-new",
            ),
        ),
    ),
)

jobs_menu_items = (
    PluginMenuItem(
        link="plugins:netbox_fortigate:fortigatescheduler_list",
        link_text=_("Schedules"),
        permissions=["netbox_fortinet.view_fortigatescheduler"],
    ),
)



menu = PluginMenu(
    label=_("Firewalls"),
    icon_class='mdi mdi-wall',
    groups=(
        (_("FortiGate"), menu_items),
        (_("Jobs"), jobs_menu_items),
        (_("Request"), request_menu_items),
    ),
)
