from django.urls import path
from .views import DashboardView, SchedulesView, HistoryView, ControlView, dashboard_api_status

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='home'),
    path('schedules/', SchedulesView.as_view(), name='schedules'),
    path('history/', HistoryView.as_view(), name='history'),
    path('control/', ControlView.as_view(), name='control'),
    path('api/status/', dashboard_api_status, name='api_status'),
]