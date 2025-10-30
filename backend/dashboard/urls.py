from django.urls import path
from .views import (
    DashboardView, SchedulesView, HistoryView, ControlView, SettingsView,
    dashboard_api_status, dashboard_api_history_stats, 
    dashboard_api_temperature_chart, dashboard_api_schedules,
    dashboard_api_manual_control
)

app_name = 'dashboard'

urlpatterns = [
    # Vistas de templates (SPA)
    path('', DashboardView.as_view(), name='home'),
    path('schedules/', SchedulesView.as_view(), name='schedules'),
    path('history/', HistoryView.as_view(), name='history'),
    path('control/', ControlView.as_view(), name='control'),
    path('settings/', SettingsView.as_view(), name='settings'),
    
    # APIs para JavaScript
    path('api/status/', dashboard_api_status, name='api_status'),
    path('api/history-stats/', dashboard_api_history_stats, name='api_history_stats'),
    path('api/temperature-chart/', dashboard_api_temperature_chart, name='api_temperature_chart'),
    path('api/schedules/', dashboard_api_schedules, name='api_schedules'),
    path('api/manual-control/', dashboard_api_manual_control, name='api_manual_control'),
]