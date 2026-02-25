from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register("devices", FortigateViewSet)
router.register("interfaces", InterfacesViewSet)
# router.register("zones", ZoneViewSet)
router.register("routing-table", RoutingTableViewSet)
# router.register("objects", ObjectViewSet)
router.register("schedules", SchedulerViewSet)

urlpatterns = router.urls
