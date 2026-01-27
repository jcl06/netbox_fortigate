from django.urls import include, path

from utilities.urls import get_model_urls

from . import views

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
    path("zones/delete/", views.FortiGateZoneDeleteView.as_view(), name="fortigatezone_bulk_delete"),
    path('zones/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigatezone'))),

    # Routes
    path("routing-table/", views.FortiGateRouteListView.as_view(), name="fortigateroute_list"),
    path("routing-table/delete/", views.FortiGateRouteBulkDeleteView.as_view(), name="fortigateroute_bulk_delete"),
    path('routing-table/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigateroute'))),

    # Objects
    path("objects/", views.FortiGateObjectListView.as_view(), name="fortigateobject_list"),
    path("objects/delete/", views.FortiGateObjectDeleteView.as_view(), name="fortigateobject_delete"),
    path('objects/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigateobject'))),

    # Requests placeholder for now
    path("requests/", views.requests_placeholder, name="requests"),
]
