from django.utils.translation import gettext as _

from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem
from netbox.navigation.menu import MENUS, MenuGroup, MenuItem, MenuItemButton

fw_menu_items = (
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

nw_menu_items = (
    PluginMenuItem(
        link="plugins:netbox_fortigate:interfaces_list",
        link_text=_("Interfaces"),
        permissions=["netbox_fortigate.view_interfaces"],
    ),
    PluginMenuItem(
        link="plugins:netbox_fortigate:zone_list",
        link_text=_("Zones"),
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
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_fortigate:scheduler_add",
                title=_("Add Job Schedule"),
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_fortigate.add_scheduler"],
            ),
        ),
    ),
)

policy_menu_items = (
    PluginMenuItem(
        link="plugins:netbox_fortigate:policy_list",
        link_text=_("Policies"),
        permissions=["netbox_fortigate.view_policy"],
    ),
)

automation = (
    MenuGroup(
        label=_("Automation"),
        items=(
            MenuItem(
                link="plugins:netbox_fortigate:check_policy",
                link_text=_("Check Policy"),
                permissions=["netbox_fortigate.view_policy"],
            ),
        )
    ),
)

menus = PluginMenu(
    label=_("Firewalls"),
    icon_class='mdi mdi-wall',
    groups=(
        (_("Firewalls"), fw_menu_items),
        (_("Network"), nw_menu_items),
        (_("Policy & Objects"), policy_menu_items)
    ),
)


def update_menu():
    for item in MENUS:
        if item.label == "Operations":
            for g in item.groups:
                if g.label == "Jobs":
                    g.items = g.items + jobs_menu_items
            item.groups = automation + item.groups
    MENUS.insert(3, menus)

