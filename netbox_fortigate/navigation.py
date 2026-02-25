from django.utils.translation import gettext as _

from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem


fw_menu_items = (
    PluginMenuItem(
        link="plugins:netbox_fortigate:fortigate_list",
        link_text=_("Firewalls"),
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_fortigate:fortigate_add",
                title=_("Add Fortigate device"),
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_fortigate.add_fortigate"],
            ),
            PluginMenuButton(
                link="plugins:netbox_fortigate:fortigate_bulk_import",
                title=_("Import Fortigate device"),
                icon_class='mdi mdi-upload',
                permissions=["netbox_fortigate.add_fortigate"],
            ),
        ),
        permissions=["netbox_fortigate.view_fortigate"],
    ),
    PluginMenuItem(
        link="plugins:netbox_fortigate:interfaces_list",
        link_text=_("Interfaces"),
        # buttons=(
        #     PluginMenuButton(
        #         link="plugins:netbox_fortigate:interface_add",
        #         title=_("Add interface"),
        #         icon_class="mdi mdi-plus-thick",
        #     ),
        # ),
        permissions=["netbox_fortigate.view_interfaces"],
    ),
    PluginMenuItem(
        link="plugins:netbox_fortigate:zone_list",
        link_text=_("Zones"),
        # buttons=(
        #     PluginMenuButton(
        #         link="plugins:netbox_fortigate:zone_add",
        #         title=_("Add zone"),
        #         icon_class="mdi mdi-plus-thick",
        #     ),
        # ),
        permissions=["netbox_fortigate.view_zone"],
    ),
    PluginMenuItem(
        link="plugins:netbox_fortigate:routingtable_list",
        link_text=_("Routing Table"),
        permissions=["netbox_fortigate.view_routingtable"],
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
        link="plugins:netbox_fortigate:scheduler_list",
        link_text=_("Schedules"),
        permissions=["netbox_fortigate.view_scheduler"],
    ),
)


menu_items = (
    PluginMenuItem(
        link="plugins:netbox_fortigate:check_policy",
        link_text=_("Check Policy"),
        permissions=["netbox_fortigate.view_policy"],
    ),
    PluginMenuItem(
        link="plugins:netbox_fortigate:fortigate_list",
        link_text=_("Fortigates"),
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_fortigate:fortigate_add",
                title=_("Add Fortigate device"),
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_fortigate.add_fortigate"],
            ),
            PluginMenuButton(
                link="plugins:netbox_fortigate:fortigate_bulk_import",
                title=_("Import Fortigate device"),
                icon_class='mdi mdi-upload',
                permissions=["netbox_fortigate.add_fortigate"],
            ),
        ),
        permissions=["netbox_fortigate.view_fortigate"],
    ),
)

menu = PluginMenu(
    label=_("Firewalls"),
    icon_class='mdi mdi-wall',
    groups=(
        (_(""), menu_items),
        # (_("Fortigate"), fw_menu_items),
        (_("Jobs"), jobs_menu_items),
        # (_("Request"), request_menu_items),
    ),
)
