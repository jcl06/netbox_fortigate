from django.utils.translation import gettext_lazy as _

from dcim.models import Device
from netbox.views import generic
from utilities.views import ViewTab
from core.filtersets import JobFilterSet
from core.models import Job, ObjectType
from core.tables import JobTable

from netbox_fortigate.models import Fortigate
from core.tables import JobTable




class DeviceJobsTabView(generic.ObjectChildrenView):
    """
    Device tab which displays jobs for the linked Fortigate, with full NetBox
    table controls (quick search, filters, configure table, pagination).
    """
    queryset = Device.objects.all()
    child_model = Job
    table = JobTable
    filterset = JobFilterSet
    actions = ()

    # This template provides the standard list UX (controls + table + paginator + config modal)
    template_name =  "netbox_fortigate/device_fortigate_tab.html"

    tab = ViewTab(
        label=_("Jobs"),
        # Show tab only if the device has a linked Fortigate (even if 0 jobs)
        badge=lambda obj: getattr(obj, "fortigate", None).jobs.count() if hasattr(obj, "fortigate") else 0,
        hide_if_empty=True,
        permission="netbox_fortigate.view_fortigatedevice",
        weight=5000,
    )

    def get_children(self, request, parent):
        """
        Return Job queryset for the linked Fortigate.
        """
        fg = getattr(parent, "fortigate", None)
        if not isinstance(fg, Fortigate):
            return Job.objects.none()

        ot = ObjectType.objects.get_for_model(Fortigate, for_concrete_model=False)

        return Job.objects.filter(
            object_type=ot,
            object_id=fg.pk,
        )

    def get_table(self, *args, **kwargs):
        """
        Hide 'object' columns because we're already inside a specific device context.
        """
        table = super().get_table(*args, **kwargs)

        for col in ("object_type", "object", "pk", "actions"):
            if col in table.columns:
                table.columns.hide(col)

        return table
    
# class DeviceJobsTabView(generic.ObjectView):
#     """
#     A Device tab that renders a NetBox-style Jobs table for the linked Fortigate.
#     """
#     queryset = Device.objects.all().filter()
#     template_name = "netbox_fortigate/device_fortigate_tab.html"

#     tab = ViewTab(
#         label=_("Jobs"),
#         badge=lambda obj: getattr(obj, "fortigate", None).jobs.count() if hasattr(obj, "fortigate") else 0,
#         hide_if_empty=True,

#         permission="netbox_fortigate.view_fortigatedevice",
#         weight=5000,
#     )

#     def get_extra_context(self, request, instance):
#         fg = getattr(instance, "fortigate", None)
#         if not isinstance(fg, Fortigate):
#             return {"fortigate": None, "table": None}

#         # Use the jobs relation provided by JobsMixin (preferred)
#         jobs = fg.jobs.all()

#         table = JobTable(data=jobs, user=request.user, exclude=('object','type'))
#         table.configure(request)
        

#         return {
#             "fortigate": fg,
#             "table": table,
#             'table_config': 'JobTable_config',
#             'table_configs': get_table_configs(table, request.user),
#         }