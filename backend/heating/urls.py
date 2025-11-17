from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.http import HttpResponse
from .views import HeatingSettingsViewSet, HeatingScheduleViewSet, HeatingLogViewSet, HeatingControlViewSet
from . import dashboard_views, charts_views
from .simple_debug import simple_debug_view

router = DefaultRouter()
router.register(r'settings', HeatingSettingsViewSet)
router.register(r'schedules', HeatingScheduleViewSet)
router.register(r'logs', HeatingLogViewSet)
router.register(r'control', HeatingControlViewSet, basename='heating-control')

app_name = 'heating'
urlpatterns = [
    path('api/', include(router.urls)),
    # Dashboard web
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard'),
    path('api/status/', dashboard_views.status_api, name='status_api'),
    # Dashboard de gráficas
    path('charts/', charts_views.charts_dashboard_view, name='charts_dashboard'),
    path('charts/api/data/', charts_views.charts_data_api, name='charts_data_api'),
    # Vista de prueba
    path('test/', dashboard_views.test_dashboard_data, name='test_dashboard_data'),
    # Debug APIs
    path('debug/', simple_debug_view, name='simple_debug'),
]