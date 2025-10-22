from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HeatingScheduleViewSet,
    HeatingControlViewSet,
    HeatingLogViewSet,
    TemperatureThresholdViewSet
)

router = DefaultRouter()
router.register(r'schedules', HeatingScheduleViewSet)
router.register(r'control', HeatingControlViewSet)
router.register(r'logs', HeatingLogViewSet)
router.register(r'thresholds', TemperatureThresholdViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]