from django.http import HttpResponse
from netbox.views import generic
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib.contenttypes.models import ContentType

from utilities.views import GetRelatedModelsMixin, ViewTab, register_model_view, ObjectPermissionRequiredMixin
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport, BulkRename, DeleteObject
from core.models import Job
from core.tables import JobTable
from dcim.models import Device

from .. import forms, tables, filtersets
from ..models import *
from ..jobs import InventoryPullRunner, RequestRunner
from ..choices import JobTypeChoices
from ..utils.policy_lookups import get_objects_values

@register_model_view(Fortigate, 'list', path='', detail=False)
class FortigateListView(generic.ObjectListView):
    queryset = Fortigate.objects.all()
    table = tables.FortigateTable
    filterset = filtersets.FortigateFilterSet


@register_model_view(Fortigate)
class FortigateView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Fortigate.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'related_models': self.get_related_models(request, instance),
        }

@register_model_view(Fortigate, 'add', detail=False)
@register_model_view(Fortigate, 'edit')
class FortigateEditView(generic.ObjectEditView):
    queryset = Fortigate.objects.all()
    form = forms.FortigateForm

@register_model_view(Fortigate, 'delete')
class FortigateDeleteView(generic.ObjectDeleteView):
    queryset = Fortigate.objects.all()

@register_model_view(Fortigate, 'bulk_delete', path='delete', detail=False)
class FortigateBulkDeleteView(generic.BulkDeleteView):
    queryset = Fortigate.objects.all()
    filterset = filtersets.FortigateFilterSet
    table = tables.FortigateTable

@register_model_view(Fortigate, 'bulk_import', path='import', detail=False)
class FortigateBulkImportView(generic.BulkImportView):
    queryset = Fortigate.objects.all()
    model_form = forms.FortigateImportForm
    

@register_model_view(Interfaces, 'list', path='', detail=False)
class InterfacesListView(generic.ObjectListView):
    queryset = Interfaces.objects.all()
    table = tables.InterfacesTable
    filterset = filtersets.InterfacesFilterSet
    actions = (BulkExport, BulkDelete)

@register_model_view(Interfaces)
class InterfacesView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Interfaces.objects.all()
    actions = (DeleteObject,)

    def get_extra_context(self, request, instance):
        child_interfaces = Interfaces.objects.restrict(request.user, 'view').filter(parent=instance)
        child_interfaces_table = tables.InterfacesTable(
            child_interfaces,
            exclude=('fortigate__device', 'parent'),
            orderable=False
        )
        child_interfaces_table.configure(request)
        
        return {
            "related_models": self.get_related_models(request, instance),
            'child_interfaces_table': child_interfaces_table,
        }

@register_model_view(Interfaces, 'delete')
class InterfacesDeleteView(generic.ObjectDeleteView):
    queryset = Interfaces.objects.all()

@register_model_view(Interfaces, "bulk_delete", path="delete", detail=False)
class InterfacesBulkDeleteView(generic.BulkDeleteView):
    queryset = Interfaces.objects.all()
    filterset = filtersets.InterfacesFilterSet
    table = tables.InterfacesTable

@register_model_view(Zone, 'list', path='', detail=False)
class ZoneListView(generic.ObjectListView):
    queryset = Zone.objects.all()
    table = tables.ZoneTable
    filterset = filtersets.ZoneFilterSet
    actions = (BulkExport, BulkDelete)

@register_model_view(Zone)
class ZoneView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Zone.objects.all()
    actions = (DeleteObject,)
    
    def get_extra_context(self, request, instance):
        interfaces = instance.interface.all()
        interfaces_table = tables.InterfacesTable(
            interfaces,
            exclude=('fortigate__device',),
            orderable=False
        )
        interfaces_table.configure(request)
        return {
            'related_models': self.get_related_models(request, instance),
            'interfaces_table': interfaces_table,
            'interfaces_count': interfaces.count(),
        }

@register_model_view(Zone, 'delete')
class ZoneDeleteView(generic.ObjectDeleteView):
    queryset = Zone.objects.all()

@register_model_view(Zone, "bulk_delete", path="delete", detail=False)
class ZoneBulkDeleteView(generic.BulkDeleteView):
    queryset = Zone.objects.all()
    filterset = filtersets.ZoneFilterSet
    table = tables.ZoneTable

@register_model_view(RoutingTable, 'list', path='', detail=False)
class RoutingTableListView(generic.ObjectListView):
    queryset = RoutingTable.objects.all()
    table = tables.RoutingTableTable
    filterset = filtersets.RoutingTableFilterSet
    actions = (BulkExport, BulkDelete)
    

@register_model_view(RoutingTable, 'delete')
class RoutingTableDeleteView(generic.ObjectDeleteView):
    queryset = RoutingTable.objects.all()

@register_model_view(RoutingTable, "bulk_delete", path="delete", detail=False)
class RoutingTableBulkDeleteView(generic.BulkDeleteView):
    queryset = RoutingTable.objects.all()
    filterset = filtersets.RoutingTableFilterSet
    table = tables.RoutingTableTable

@register_model_view(Object, 'list', path='', detail=False)
class ObjectListView(generic.ObjectListView):
    queryset = Object.objects.all()
    table = tables.ObjectTable
    filterset = filtersets.ObjectFilterSet
    filterset_form = forms.ObjectFilterForm
    actions = (BulkExport, BulkDelete)


@register_model_view(Object)
class ObjectView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Object.objects.all()
    actions = (DeleteObject,)

    def get_extra_context(self, request, instance):
        return {
            'related_models': self.get_related_models(request, instance),
        }
    

@register_model_view(Object, 'delete')
class ObjectDeleteView(generic.ObjectDeleteView):
    queryset = Object.objects.all()

@register_model_view(Object, "bulk_delete", path="delete", detail=False)
class ObjectBulkDeleteView(generic.BulkDeleteView):
    queryset = Object.objects.all()
    filterset = filtersets.ObjectFilterSet
    table = tables.ObjectTable



def requests_placeholder(request):
    return HttpResponse("netbox_fortigate: OK (Fortigate requests placeholder)")



class ScheduleRunNowView(ObjectPermissionRequiredMixin, View):
    queryset = Scheduler.objects.all()

    def get_required_permission(self):
        return "netbox_fortigate.change_scheduler"

    def post(self, request, pk: int):
        schedule = get_object_or_404(self.queryset, pk=pk)

        runner = (
            InventoryPullRunner
            if schedule.job_type == JobTypeChoices.INVENTORY_PULL
            else RequestRunner
        )

        runner.enqueue(
            instance=schedule,
            user=request.user,
            name=f"Manual Pull: {schedule.name}",
            schedule_id=schedule.pk,
            data={
                "trigger": "manual",
                "schedule_id": schedule.pk,
                "schedule_name": schedule.name,
                "job_type": schedule.job_type,
            },
        )

        messages.success(request, f"Enqueued: {runner.Meta.name} for '{schedule.name}'.")
        return redirect(schedule.get_absolute_url())
    
    


class FortigatePullInventoryView(ObjectPermissionRequiredMixin, View):
    queryset = Fortigate.objects.all()

    def get_required_permission(self):
        return "dcim.change_device"

    def get_object(self, parent: int | None = None, **kwargs):
        """
        Return an object for editing. If parent is provided, resolve the Fortigate.
        Otherwise resolve the core Device.
        """
        if parent:
            queryset = Device.objects.all()
            return get_object_or_404(queryset, pk=parent)
        return get_object_or_404(self.queryset, **kwargs)

    def post(self, request, **kwargs):
        parent = request.POST.get("parent") or None

        # Keep your original redirect target behavior
        obj = fg = get_object_or_404(self.queryset, **kwargs)
        if parent:
            obj = self.get_object(parent=int(parent), **kwargs)

        device = get_object_or_404(Device, fortigate=fg)

        # Enqueue job and then persist job.data explicitly
        InventoryPullRunner.enqueue(
            instance=fg,
            user=request.user,
            name=f"{InventoryPullRunner.name}: {device.name}",
            fortigate_id=fg.pk,
            data={
                "trigger": "manual",
                "fortigate_id": fg.pk,
                "device_name": device.name,
                "device_id": device.pk,
            },
        )

        messages.success(request, f"Enqueued inventory pull for '{device.name}'.")
        return redirect(obj.get_absolute_url())


@register_model_view(Scheduler, 'list', path='', detail=False)
class ScheduleListView(generic.ObjectListView):
    queryset = Scheduler.objects.all()
    table = tables.SchedulerTable
    filterset = filtersets.SchedulerFilterSet
    actions = (AddObject, BulkExport, BulkDelete)


@register_model_view(Scheduler)
class ScheduleView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Scheduler.objects.all()

    def get_extra_context(self, request, instance):
        # Show jobs related to THIS schedule, for the correct runner based on job_type
        if instance.job_type == JobTypeChoices.INVENTORY_PULL:
            runner = InventoryPullRunner
        else:
            runner = RequestRunner

        return {
            # "jobs": jobs,
            "runner_name": runner.Meta.name,
        }

@register_model_view(Scheduler, 'add', detail=False)
@register_model_view(Scheduler, 'edit')
class ScheduleEditView(generic.ObjectEditView):
    queryset = Scheduler.objects.all()
    form = forms.SchedulerForm

@register_model_view(Scheduler, 'delete')
class ScheduleDeleteView(generic.ObjectDeleteView):
    queryset = Scheduler.objects.all()

@register_model_view(Scheduler, "bulk_delete", path="delete", detail=False)
class ScheduleBulkDeleteView(generic.BulkDeleteView):
    queryset = Scheduler.objects.all()
    filterset = filtersets.SchedulerFilterSet
    table = tables.SchedulerTable


class SchedulerJobsView(generic.ObjectJobsView):
    def get_jobs(self, instance):
        object_type = ContentType.objects.get_for_model(instance)
        qs = Job.objects.filter(object_type=object_type, object_id=instance.id)

        # Optional: filter by runner names if you want
        return qs.filter(name__in=[
            InventoryPullRunner.name,
            RequestRunner.name,
        ])
    



@register_model_view(Policy)
class PolicyView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Policy.objects.all()
    actions = (DeleteObject,)

    def get_extra_context(self, request, instance):
        users = []
        if instance.users.all():
            users.extend(get_objects_values(instance.users.all(), False, "User"))
        if instance.groups.all():
            users.extend(get_objects_values(instance.groups.all(), False, "UserGroup"))

        return {
            'related_models': self.get_related_models(request, instance),
            'schedule': get_objects_values([instance.schedule], True),
            'source_interface': get_objects_values(instance.source_interface.all(), True),
            'destination_interface': get_objects_values(instance.destination_interface.all(), True),
            'source_address': get_objects_values(instance.source_address.all(), True),
            'destination_address': get_objects_values(instance.destination_address.all(), True),
            'services': get_objects_values(instance.service.all(), True),
            'users': ", ".join(users),
        }

@register_model_view(Policy, 'list', path='', detail=False)
class PolicyListView(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = Policy.objects.all()
    table = tables.PolicyTable
    filterset = filtersets.PolicyFilterSet

@register_model_view(Policy, 'delete')
class PolicyDeleteView(generic.ObjectDeleteView):
    queryset = Policy.objects.all()


@register_model_view(Policy, "bulk_delete", path="delete", detail=False)
class PolicyBulkDeleteView(generic.BulkDeleteView):
    queryset = Policy.objects.all()
    table = tables.PolicyTable
    filterset = filtersets.PolicyFilterSet




@register_model_view(Address, 'list', path='', detail=False)
class AddressList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = Address.objects.all()
    table = tables.AddressTable
    filterset = filtersets.AddressFilterSet
    # filterset_form = forms.AddressFilterForm

@register_model_view(Address, "delete")
class AddressDeleteView(generic.ObjectDeleteView):
    queryset = Address.objects.all()

@register_model_view(Address, "bulk_delete", path="delete", detail=False)
class AddressBulkDeleteView(generic.BulkDeleteView):
    queryset = Address.objects.all()
    filterset = filtersets.AddressFilterSet
    table = tables.AddressTable


@register_model_view(AddressGroup, 'list', path='', detail=False)
class AddressGroupList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = AddressGroup.objects.all()
    table = tables.AddressGroupTable
    filterset = filtersets.AddressGroupFilterSet
    # filterset_form = forms.AddressGroupFilterForm

@register_model_view(AddressGroup, "delete")
class AddressGroupDeleteView(generic.ObjectDeleteView):
    queryset = AddressGroup.objects.all()

@register_model_view(AddressGroup, "bulk_delete", path="delete", detail=False)
class AddressGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = AddressGroup.objects.all()
    filterset = filtersets.AddressGroupFilterSet
    table = tables.AddressGroupTable


@register_model_view(Services, 'list', path='', detail=False)
class ServicesList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = Services.objects.all()
    table = tables.ServicesTable
    filterset = filtersets.ServicesFilterSet
    # filterset_form = forms.ServicesFilterForm

@register_model_view(Services, "delete")
class ServicesDeleteView(generic.ObjectDeleteView):
    queryset = Services.objects.all()

@register_model_view(Services, "bulk_delete", path="delete", detail=False)
class ServicesBulkDeleteView(generic.BulkDeleteView):
    queryset = Services.objects.all()
    filterset = filtersets.ServicesFilterSet
    table = tables.ServicesTable


@register_model_view(ServiceGroup, 'list', path='', detail=False)
class ServiceGroupList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = ServiceGroup.objects.all()
    table = tables.ServiceGroupTable
    filterset = filtersets.ServiceGroupFilterSet
    # filterset_form = forms.ServiceGroupFilterForm

@register_model_view(ServiceGroup, "delete")
class ServiceGroupDeleteView(generic.ObjectDeleteView):
    queryset = ServiceGroup.objects.all()

@register_model_view(ServiceGroup, "bulk_delete", path="delete", detail=False)
class ServiceGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = ServiceGroup.objects.all()
    filterset = filtersets.ServiceGroupFilterSet
    table = tables.ServiceGroupTable


@register_model_view(VIP, 'list', path='', detail=False)
class VIPList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = VIP.objects.all()
    table = tables.VIPTable
    filterset = filtersets.VIPFilterSet
    # filterset_form = forms.VIPFilterForm

@register_model_view(VIP, "delete")
class VIPDeleteView(generic.ObjectDeleteView):
    queryset = VIP.objects.all()

@register_model_view(VIP, "bulk_delete", path="delete", detail=False)
class VIPBulkDeleteView(generic.BulkDeleteView):
    queryset = VIP.objects.all()
    filterset = filtersets.VIPFilterSet
    table = tables.VIPTable


@register_model_view(VIPGroup, 'list', path='', detail=False)
class VIPGroupList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = VIPGroup.objects.all()
    table = tables.VIPGroupTable
    filterset = filtersets.VIPGroupFilterSet
    # filterset_form = forms.VIPGroupFilterForm

@register_model_view(VIPGroup, "delete")
class VIPGroupDeleteView(generic.ObjectDeleteView):
    queryset = VIPGroup.objects.all()

@register_model_view(VIPGroup, "bulk_delete", path="delete", detail=False)
class VIPGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = VIPGroup.objects.all()
    filterset = filtersets.VIPGroupFilterSet
    table = tables.VIPGroupTable


@register_model_view(ScheduleOnetime, 'list', path='', detail=False)
class ScheduleOnetimeList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = ScheduleOnetime.objects.all()
    table = tables.ScheduleOnetimeTable
    filterset = filtersets.ScheduleOnetimeFilterSet
    # filterset_form = forms.ScheduleOnetimeFilterForm

@register_model_view(ScheduleOnetime, "delete")
class ScheduleOnetimeDeleteView(generic.ObjectDeleteView):
    queryset = ScheduleOnetime.objects.all()

@register_model_view(ScheduleOnetime, "bulk_delete", path="delete", detail=False)
class ScheduleOnetimeBulkDeleteView(generic.BulkDeleteView):
    queryset = ScheduleOnetime.objects.all()
    filterset = filtersets.ScheduleOnetimeFilterSet
    table = tables.ScheduleOnetimeTable


@register_model_view(ScheduleRecurring, 'list', path='', detail=False)
class ScheduleRecurringList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = ScheduleRecurring.objects.all()
    table = tables.ScheduleRecurringTable
    filterset = filtersets.ScheduleRecurringFilterSet
    # filterset_form = forms.ScheduleRecurringFilterForm

@register_model_view(ScheduleRecurring, "delete")
class ScheduleRecurringDeleteView(generic.ObjectDeleteView):
    queryset = ScheduleRecurring.objects.all()

@register_model_view(ScheduleRecurring, "bulk_delete", path="delete", detail=False)
class ScheduleRecurringBulkDeleteView(generic.BulkDeleteView):
    queryset = ScheduleRecurring.objects.all()
    filterset = filtersets.ScheduleRecurringFilterSet
    table = tables.ScheduleRecurringTable
    

@register_model_view(ScheduleGroup, 'list', path='', detail=False)
class ScheduleGroupList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = ScheduleGroup.objects.all()
    table = tables.ScheduleGroupTable
    filterset = filtersets.ScheduleGroupFilterSet
    # filterset_form = forms.ScheduleGroupFilterForm

@register_model_view(ScheduleGroup, "delete")
class ScheduleGroupDeleteView(generic.ObjectDeleteView):
    queryset = ScheduleGroup.objects.all()

@register_model_view(ScheduleGroup, "bulk_delete", path="delete", detail=False)
class ScheduleGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = ScheduleGroup.objects.all()
    filterset = filtersets.ScheduleGroupFilterSet
    table = tables.ScheduleGroupTable


@register_model_view(User, 'list', path='', detail=False)
class UserList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = User.objects.all()
    table = tables.UserTable
    filterset = filtersets.UserFilterSet
    # filterset_form = forms.UserFilterForm

@register_model_view(User, "delete")
class UserDeleteView(generic.ObjectDeleteView):
    queryset = User.objects.all()

@register_model_view(User, "bulk_delete", path="delete", detail=False)
class UserBulkDeleteView(generic.BulkDeleteView):
    queryset = User.objects.all()
    filterset = filtersets.UserFilterSet
    table = tables.UserTable


@register_model_view(AuthenticationServer, 'list', path='', detail=False)
class AuthenticationServerList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = AuthenticationServer.objects.all()
    table = tables.AuthenticationServerTable
    filterset = filtersets.AuthenticationServerFilterSet
    # filterset_form = forms.AuthenticationServerFilterForm

@register_model_view(AuthenticationServer, "delete")
class AuthenticationServerDeleteView(generic.ObjectDeleteView):
    queryset = AuthenticationServer.objects.all()

@register_model_view(AuthenticationServer, "bulk_delete", path="delete", detail=False)
class AuthenticationServerBulkDeleteView(generic.BulkDeleteView):
    queryset = AuthenticationServer.objects.all()
    filterset = filtersets.AuthenticationServerFilterSet
    table = tables.AuthenticationServerTable


@register_model_view(UserGroup, 'list', path='', detail=False)
class UserGroupList(generic.ObjectListView):
    actions = (BulkExport, BulkDelete)
    queryset = UserGroup.objects.all()
    table = tables.UserGroupTable
    filterset = filtersets.UserGroupFilterSet
    # filterset_form = forms.UserGroupFilterForm

@register_model_view(UserGroup, "delete")
class UserGroupDeleteView(generic.ObjectDeleteView):
    queryset = UserGroup.objects.all()

@register_model_view(UserGroup, "bulk_delete", path="delete", detail=False)
class UserGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = UserGroup.objects.all()
    filterset = filtersets.UserGroupFilterSet
    table = tables.UserGroupTable