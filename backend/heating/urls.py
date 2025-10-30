from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HeatingScheduleViewSet,
    HeatingControlViewSet,
    HeatingLogViewSet,
    HeatingSettingsViewSet,
    dashboard,
    settings_view
)

router = DefaultRouter()
router.register(r'schedules', HeatingScheduleViewSet)
router.register(r'control', HeatingControlViewSet)
router.register(r'logs', HeatingLogViewSet)
router.register(r'settings', HeatingSettingsViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('', dashboard, name='heating-dashboard'),
    path('settings/', settings_view, name='heating-settings'),
]