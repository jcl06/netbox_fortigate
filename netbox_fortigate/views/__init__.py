from django.http import HttpResponse
from netbox.views import generic
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib.contenttypes.models import ContentType

from utilities.views import GetRelatedModelsMixin, ViewTab, register_model_view, ObjectPermissionRequiredMixin
from core.models import Job
from core.tables import JobTable
from dcim.models import Device

from .. import forms, tables, filtersets
from ..models import *
from ..jobs import FortiGateInventoryPullRunner, FortiGateRequestRunner
from ..choices import JobTypeChoices


class FortiGateDeviceListView(generic.ObjectListView):
    queryset = FortiGateDevice.objects.all()
    table = tables.FortiGateDeviceTable
    filterset = filtersets.FortiGateDeviceFilterSet


@register_model_view(FortiGateDevice)
class FortiGateDeviceView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = FortiGateDevice.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'related_models': self.get_related_models(request, instance),
        }

@register_model_view(FortiGateDevice, 'edit')
class FortiGateDeviceEditView(generic.ObjectEditView):
    queryset = FortiGateDevice.objects.all()
    form = forms.FortiGateDeviceForm

@register_model_view(FortiGateDevice, 'delete')
class FortiGateDeviceDeleteView(generic.ObjectDeleteView):
    queryset = FortiGateDevice.objects.all()


class FortiGateDeviceBulkDeleteView(generic.BulkDeleteView):
    queryset = FortiGateDevice.objects.all()
    filterset = filtersets.FortiGateDeviceFilterSet
    table = tables.FortiGateDeviceTable

class FortiGateDeviceBulkImportView(generic.BulkImportView):
    queryset = FortiGateDevice.objects.all()
    model_form = forms.FortiGateDeviceImportForm
    


class FortiGateInterfaceListView(generic.ObjectListView):
    queryset = FortiGateInterface.objects.all()
    table = tables.FortiGateInterfaceTable
    filterset = filtersets.FortiGateInterfaceFilterSet

@register_model_view(FortiGateInterface)
class FortiGateInterfaceView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = FortiGateInterface.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'related_models': self.get_related_models(request, instance),
        }

@register_model_view(FortiGateInterface, 'delete')
class FortiGateInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = FortiGateInterface.objects.all()

class FortiGateInterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = FortiGateInterface.objects.all()
    filterset = filtersets.FortiGateInterfaceFilterSet
    table = tables.FortiGateInterfaceTable


class FortiGateZoneListView(generic.ObjectListView):
    queryset = FortiGateZone.objects.all()
    table = tables.FortiGateZoneTable
    filterset = filtersets.FortiGateZoneFilterSet

@register_model_view(FortiGateZone)
class FortiGateZoneView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = FortiGateZone.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'related_models': self.get_related_models(request, instance),
        }

@register_model_view(FortiGateZone, 'delete')
class FortiGateZoneDeleteView(generic.ObjectDeleteView):
    queryset = FortiGateZone.objects.all()

class FortiGatZoneBulkDeleteView(generic.BulkDeleteView):
    queryset = FortiGateZone.objects.all()
    filterset = filtersets.FortiGateZoneFilterSet
    table = tables.FortiGateZoneTable

class FortiGateRouteListView(generic.ObjectListView):
    queryset = FortiGateRoute.objects.all()
    table = tables.FortiGateRouteTable
    filterset = filtersets.FortiGateRouteFilterSet

@register_model_view(FortiGateRoute)
class FortiGateRouteView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = FortiGateRoute.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'related_models': self.get_related_models(request, instance),
        }

@register_model_view(FortiGateRoute, 'delete')
class FortiGateRouteDeleteView(generic.ObjectDeleteView):
    queryset = FortiGateRoute.objects.all()


class FortiGateRouteBulkDeleteView(generic.BulkDeleteView):
    queryset = FortiGateRoute.objects.all()
    filterset = filtersets.FortiGateRouteFilterSet
    table = tables.FortiGateRouteTable

class FortiGateObjectListView(generic.ObjectListView):
    queryset = FortiGateObject.objects.all()
    table = tables.FortiGateObjectTable
    filterset = filtersets.FortiGateObjectFilterSet
    filterset_form = forms.FortiGateObjectFilterForm


@register_model_view(FortiGateObject)
class FortiGateObjectView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = FortiGateObject.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'related_models': self.get_related_models(request, instance),
        }
    

@register_model_view(FortiGateObject, 'delete')
class FortiGateObjectDeleteView(generic.ObjectDeleteView):
    queryset = FortiGateObject.objects.all()


class FortiGatObjectBulkDeleteView(generic.BulkDeleteView):
    queryset = FortiGateObject.objects.all()
    filterset = filtersets.FortiGateObjectFilterSet
    table = tables.FortiGateObjectTable



def requests_placeholder(request):
    return HttpResponse("netbox_fortigate: OK (FortiGate requests placeholder)")



class FortiGateScheduleRunNowView(ObjectPermissionRequiredMixin, View):
    queryset = FortiGateScheduler.objects.all()

    def get_required_permission(self):
        return "netbox_fortigate.change_fortigatescheduler"

    def post(self, request, pk: int):
        schedule = get_object_or_404(self.queryset, pk=pk)

        runner = (
            FortiGateInventoryPullRunner
            if schedule.job_type == JobTypeChoices.INVENTORY_PULL
            else FortiGateRequestRunner
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
    
    


class FortiGateDevicePullInventoryView(ObjectPermissionRequiredMixin, View):
    queryset = FortiGateDevice.objects.all()

    def get_required_permission(self):
        return "dcim.change_device"

    def get_object(self, parent: int | None = None, **kwargs):
        """
        Return an object for editing. If parent is provided, resolve the FortiGateDevice.
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
        FortiGateInventoryPullRunner.enqueue(
            instance=fg,
            user=request.user,
            name=f"{FortiGateInventoryPullRunner.name}: {device.name}",
            device_id=device.pk,
            data={
                "trigger": "manual",
                "device_id": device.pk,
                "device_name": device.name,
                "fortigate_device_id": fg.pk,
            },
        )

        messages.success(request, f"Enqueued inventory pull for '{device.name}'.")
        return redirect(obj.get_absolute_url())


class FortiGateScheduleListView(generic.ObjectListView):
    queryset = FortiGateScheduler.objects.all()
    table = tables.FortiGateSchedulerTable
    filterset = filtersets.FortiGateSchedulerFilterSet


@register_model_view(FortiGateScheduler)
class FortiGateScheduleView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = FortiGateScheduler.objects.all()

    def get_extra_context(self, request, instance):
        # Show jobs related to THIS schedule, for the correct runner based on job_type
        if instance.job_type == JobTypeChoices.INVENTORY_PULL:
            runner = FortiGateInventoryPullRunner
        else:
            runner = FortiGateRequestRunner

        return {
            # "jobs": jobs,
            "runner_name": runner.Meta.name,
        }


@register_model_view(FortiGateScheduler, 'edit')
class FortiGateScheduleEditView(generic.ObjectEditView):
    queryset = FortiGateScheduler.objects.all()
    form = forms.FortiGateSchedulerForm

@register_model_view(FortiGateScheduler, 'delete')
class FortiGateScheduleDeleteView(generic.ObjectDeleteView):
    queryset = FortiGateScheduler.objects.all()

class FortiGateScheduleBulkDeleteView(generic.BulkDeleteView):
    queryset = FortiGateScheduler.objects.all()
    filterset = filtersets.FortiGateSchedulerFilterSet
    table = tables.FortiGateSchedulerTable


class FortiGateSchedulerJobsView(generic.ObjectJobsView):
    def get_jobs(self, instance):
        object_type = ContentType.objects.get_for_model(instance)
        qs = Job.objects.filter(object_type=object_type, object_id=instance.id)

        # Optional: filter by runner names if you want
        return qs.filter(name__in=[
            FortiGateInventoryPullRunner.name,
            FortiGateRequestRunner.name,
        ])
    


