from django.urls import include, path

from utilities.urls import get_model_urls
from .models import FortiGateScheduler
from . import views
from .views.check_policy import PolicyView, DrawPathView, draw_path, policy_view

app_name = "netbox_fortigate"

urlpatterns = [
    # FortiGateDevice CRUD
    path("firewalls/", views.FortiGateDeviceListView.as_view(), name="fortigatedevice_list"),
    path("firewalls/add/", views.FortiGateDeviceEditView.as_view(), name="fortigatedevice_add"),
    path('firewalls/import/', views.FortiGateDeviceBulkImportView.as_view(), name='fortigatedevice_import'),
    path("firewalls/delete/", views.FortiGateDeviceBulkDeleteView.as_view(), name="fortigatedevice_bulk_delete"),
    path('firewalls/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigatedevice'))),

    # Interfaces
    path("interfaces/", views.FortiGateInterfaceListView.as_view(), name="fortigateinterface_list"),
    path("interfaces/delete/", views.FortiGateInterfaceBulkDeleteView.as_view(), name="fortigateinterface_bulk_delete"),
    path('interfaces/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigateinterface'))),

    # Zones
    path("zones/", views.FortiGateZoneListView.as_view(), name="fortigatezone_list"),
    path("zones/delete/", views.FortiGateZoneBulkDeleteView.as_view(), name="fortigatezone_bulk_delete"),
    path('zones/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigatezone'))),

    # Routes
    path("routing-table/", views.FortiGateRouteListView.as_view(), name="fortigateroute_list"),
    path("routing-table/delete/", views.FortiGateRouteBulkDeleteView.as_view(), name="fortigateroute_bulk_delete"),
    path('routing-table/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigateroute'))),

    # Objects
    path("objects/", views.FortiGateObjectListView.as_view(), name="fortigateobject_list"),
    path("objects/delete/", views.FortiGateObjectDeleteView.as_view(), name="fortigateobject_bulk_delete"),
    path('objects/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigateobject'))),

    # Scheduler
    path("schedules/", views.FortiGateScheduleListView.as_view(), name="fortigatescheduler_list"),
    path("schedules/add/", views.FortiGateScheduleEditView.as_view(), name="fortigatescheduler_add"),
    path("schedules/delete/", views.FortiGateScheduleBulkDeleteView.as_view(), name="fortigatescheduler_bulk_delete"),
    path('schedules/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigatescheduler'))),
    path("schedules/<int:pk>/run-now/", views.FortiGateScheduleRunNowView.as_view(), name="fortigatescheduler_run_now"),
    path("schedules/<int:pk>/jobs/", views.FortiGateSchedulerJobsView.as_view(), {"model": FortiGateScheduler}, name="fortigatescheduler_jobs"),

    path("devices/<int:pk>/pull-inventory/", views.FortiGateDevicePullInventoryView.as_view(), name="device_pull_inventory",),


    # Requests placeholder for now
    path("requests/", views.requests_placeholder, name="requests"),
    path('check-policy/', DrawPathView.as_view(), name='check_policy'),
    path('check-policy/<int:fortigate>/<int:pid>/', PolicyView.as_view(), name ='policy_view'),
    path('check-policy1/', draw_path, name='check_policy1'),
    path('check-policy1/<int:fortigate>/<int:pid>/', policy_view, name ='policy_view1'),
]
