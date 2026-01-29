from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register("devices", FortiGateDeviceViewSet)
router.register("interfaces", FortiGateInterfaceViewSet)
# router.register("zones", FortiGateZoneViewSet)
router.register("routing-table", FortiGateRouteViewSet)
# router.register("objects", FortiGateObjectViewSet)
router.register("schedules", FortiGateSchedulerViewSet)

urlpatterns = router.urls
