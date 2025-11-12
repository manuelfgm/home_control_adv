from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HeatingSettingsViewSet, HeatingScheduleViewSet, HeatingLogViewSet, HeatingControlViewSet

router = DefaultRouter()
router.register(r'settings', HeatingSettingsViewSet)
router.register(r'schedules', HeatingScheduleViewSet)
router.register(r'logs', HeatingLogViewSet)
router.register(r'control', HeatingControlViewSet, basename='heating-control')

app_name = 'heating'
urlpatterns = [
    path('api/', include(router.urls)),
]