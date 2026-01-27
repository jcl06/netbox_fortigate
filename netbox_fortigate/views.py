from django.http import HttpResponse
from netbox.views import generic
from utilities.views import GetRelatedModelsMixin, ViewTab, register_model_view

from . import forms, tables, filtersets
from .models import *




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
