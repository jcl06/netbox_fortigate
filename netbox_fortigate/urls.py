from django.urls import include, path

from utilities.urls import get_model_urls
from .models import Scheduler
from . import views
from .views.check_policy import PolicyView, DrawPathView, draw_path, policy_view

app_name = "netbox_fortigate"

urlpatterns = [
    # Fortigate CRUD
    path('firewalls/', include(get_model_urls('netbox_fortigate', 'fortigate', detail=False))),
    # path("firewalls/", views.FortigateListView.as_view(), name="fortigatedevice_list"),
    # path("firewalls/add/", views.FortigateEditView.as_view(), name="fortigatedevice_add"),
    # path('firewalls/import/', views.FortigateBulkImportView.as_view(), name='fortigatedevice_import'),
    # path("firewalls/delete/", views.FortigateBulkDeleteView.as_view(), name="fortigatedevice_bulk_delete"),
    path('firewalls/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigate'))),

    # Interfaces
    path("interfaces/", views.InterfacesListView.as_view(), name="interfaces_list"),
    path("interfaces/delete/", views.InterfacesBulkDeleteView.as_view(), name="interfaces_bulk_delete"),
    path('interfaces/<int:pk>/', include(get_model_urls('netbox_fortigate', 'interfaces'))),

    # Zones
    path("zones/", views.ZoneListView.as_view(), name="zone_list"),
    path("zones/delete/", views.ZoneBulkDeleteView.as_view(), name="zone_bulk_delete"),
    path('zones/<int:pk>/', include(get_model_urls('netbox_fortigate', 'zone'))),

    # Routes
    path("routing-table/", views.RoutingTableListView.as_view(), name="routingtable_list"),
    path("routing-table/delete/", views.RoutingTableBulkDeleteView.as_view(), name="routingtable_bulk_delete"),
    path('routing-table/<int:pk>/', include(get_model_urls('netbox_fortigate', 'routingtable'))),

    # Objects
    path("objects/", views.ObjectListView.as_view(), name="object_list"),
    path("objects/delete/", views.ObjectDeleteView.as_view(), name="object_bulk_delete"),
    path('objects/<int:pk>/', include(get_model_urls('netbox_fortigate', 'object'))),

    # Scheduler
    path("schedules/", views.ScheduleListView.as_view(), name="scheduler_list"),
    path("schedules/add/", views.ScheduleEditView.as_view(), name="scheduler_add"),
    path("schedules/delete/", views.ScheduleBulkDeleteView.as_view(), name="scheduler_bulk_delete"),
    path('schedules/<int:pk>/', include(get_model_urls('netbox_fortigate', 'scheduler'))),
    path("schedules/<int:pk>/run-now/", views.ScheduleRunNowView.as_view(), name="scheduler_run_now"),
    path("schedules/<int:pk>/jobs/", views.SchedulerJobsView.as_view(), {"model": Scheduler}, name="scheduler_jobs"),

    path("devices/<int:pk>/pull-inventory/", views.FortigatePullInventoryView.as_view(), name="device_pull_inventory",),


    # Requests placeholder for now
    path("requests/", views.requests_placeholder, name="requests"),
    path('check-policy/', DrawPathView.as_view(), name='check_policy'),
    path('check-policy/<int:fortigate>/<int:pid>/', PolicyView.as_view(), name ='policy_view'),
]
