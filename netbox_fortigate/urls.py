from django.urls import include, path

from utilities.urls import get_model_urls
from .models import Scheduler
from . import views
from .views.check_policy import PolicyView, DrawPathView

app_name = "netbox_fortigate"

urlpatterns = [
    # Fortigate CRUD
    path('firewalls/', include(get_model_urls('netbox_fortigate', 'fortigate', detail=False))),
    path('firewalls/<int:pk>/', include(get_model_urls('netbox_fortigate', 'fortigate'))),

    # Interfaces
    path("interfaces/", include(get_model_urls('netbox_fortigate', 'interfaces', detail=False))),
    path('interfaces/<int:pk>/', include(get_model_urls('netbox_fortigate', 'interfaces'))),

    # Zones
    path("zones/", include(get_model_urls('netbox_fortigate', 'zone', detail=False))),
    path('zones/<int:pk>/', include(get_model_urls('netbox_fortigate', 'zone'))),

    # Routes
    path("routing-table/", include(get_model_urls('netbox_fortigate', 'routingtable', detail=False))),
    path('routing-table/<int:pk>/', include(get_model_urls('netbox_fortigate', 'routingtable'))),

    # Objects
    path("objects/", include(get_model_urls('netbox_fortigate', 'object', detail=False))),
    path('objects/<int:pk>/', include(get_model_urls('netbox_fortigate', 'object'))),

    # Scheduler
    path("schedules/", include(get_model_urls('netbox_fortigate', 'scheduler', detail=False))),
    path('schedules/<int:pk>/', include(get_model_urls('netbox_fortigate', 'scheduler'))),

     # --- Addressing ---
    path("addresses/", include(get_model_urls("netbox_fortigate", "address", detail=False))),
    path("addresses/<int:pk>/", include(get_model_urls("netbox_fortigate", "address"))),

    path("address-groups/", include(get_model_urls("netbox_fortigate", "addressgroup", detail=False))),
    path("address-groups/<int:pk>/", include(get_model_urls("netbox_fortigate", "addressgroup"))),

    # --- Services ---
    path("services/", include(get_model_urls("netbox_fortigate", "services", detail=False))),
    path("services/<int:pk>/", include(get_model_urls("netbox_fortigate", "services"))),

    path("service-groups/", include(get_model_urls("netbox_fortigate", "servicegroup", detail=False))),
    path("service-groups/<int:pk>/", include(get_model_urls("netbox_fortigate", "servicegroup"))),

    # --- VIPs ---
    path("vips/", include(get_model_urls("netbox_fortigate", "vip", detail=False))),
    path("vips/<int:pk>/", include(get_model_urls("netbox_fortigate", "vip"))),

    path("vip-groups/", include(get_model_urls("netbox_fortigate", "vipgroup", detail=False))),
    path("vip-groups/<int:pk>/", include(get_model_urls("netbox_fortigate", "vipgroup"))),

    # --- Schedules ---
    path("schedule-onetime/", include(get_model_urls("netbox_fortigate", "scheduleonetime", detail=False))),
    path("schedule-onetime/<int:pk>/", include(get_model_urls("netbox_fortigate", "scheduleonetime"))),

    path("schedule-recurring/", include(get_model_urls("netbox_fortigate", "schedulerecurring", detail=False))),
    path("schedule-recurring/<int:pk>/", include(get_model_urls("netbox_fortigate", "schedulerecurring"))),

    path("schedule-groups/", include(get_model_urls("netbox_fortigate", "schedulegroup", detail=False))),
    path("schedule-groups/<int:pk>/", include(get_model_urls("netbox_fortigate", "schedulegroup"))),

    # --- Users / auth ---
    path("users/", include(get_model_urls("netbox_fortigate", "user", detail=False))),
    path("users/<int:pk>/", include(get_model_urls("netbox_fortigate", "user"))),

    path("auth-servers/", include(get_model_urls("netbox_fortigate", "authenticationserver", detail=False))),
    path("auth-servers/<int:pk>/", include(get_model_urls("netbox_fortigate", "authenticationserver"))),

    path("user-groups/", include(get_model_urls("netbox_fortigate", "usergroup", detail=False))),
    path("user-groups/<int:pk>/", include(get_model_urls("netbox_fortigate", "usergroup"))),

    # --- Policy objects ---
    path("policies/", include(get_model_urls("netbox_fortigate", "policy", detail=False))),
    path("policies/<int:pk>/", include(get_model_urls("netbox_fortigate", "policy"))),

    path("profile-groups/", include(get_model_urls("netbox_fortigate", "profilegroup", detail=False))),
    path("profile-groups/<int:pk>/", include(get_model_urls("netbox_fortigate", "profilegroup"))),

    # Misc
    path("schedules/<int:pk>/run-now/", views.ScheduleRunNowView.as_view(), name="scheduler_run_now"),
    path("schedules/<int:pk>/jobs/", views.SchedulerJobsView.as_view(), {"model": Scheduler}, name="scheduler_jobs"),
    path("devices/<int:pk>/pull-inventory/", views.FortigatePullInventoryView.as_view(), name="device_pull_inventory",),
    
    # Requests placeholder for now
    path("requests/", views.requests_placeholder, name="requests"),
    path('check-policy/', DrawPathView.as_view(), name='check_policy'),
    path('check-policy/<int:fortigate>/<int:pid>/', PolicyView.as_view(), name ='policy_view'),
]
