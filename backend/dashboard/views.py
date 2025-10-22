from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView
from sensors.models import SensorReading, SensorStatus
from heating.models import HeatingControl, HeatingSchedule, HeatingLog
from datetime import timedelta
from django.utils import timezone


class DashboardView(TemplateView):
    """Vista principal del dashboard"""
    template_name = 'dashboard/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener datos recientes para el contexto inicial
        context['latest_temp'] = SensorReading.objects.filter(
            sensor_type='temperature'
        ).order_by('-timestamp').first()
        
        context['heating_control'] = HeatingControl.objects.filter(
            controller_id='main_heating'
        ).first()
        
        return context


class SchedulesView(TemplateView):
    """Vista para configuración de horarios"""
    template_name = 'dashboard/schedules.html'


class HistoryView(TemplateView):
    """Vista para histórico de datos"""
    template_name = 'dashboard/history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas de los últimos 7 días
        week_ago = timezone.now() - timedelta(days=7)
        
        context['heating_logs_count'] = HeatingLog.objects.filter(
            timestamp__gte=week_ago
        ).count()
        
        context['temperature_readings_count'] = SensorReading.objects.filter(
            sensor_type='temperature',
            timestamp__gte=week_ago
        ).count()
        
        return context


class ControlView(TemplateView):
    """Vista para control manual"""
    template_name = 'dashboard/control.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['heating_control'] = HeatingControl.objects.filter(
            controller_id='main_heating'
        ).first()
        
        context['active_schedules'] = HeatingSchedule.objects.filter(
            is_active=True
        ).order_by('day_of_week', 'start_time')
        
        return context


def dashboard_api_status(request):
    """API endpoint para obtener estado general del sistema"""
    try:
        # Estado de sensores
        sensors = SensorStatus.objects.filter(is_active=True)
        sensors_data = []
        
        for sensor in sensors:
            latest_temp = SensorReading.objects.filter(
                sensor_id=sensor.sensor_id,
                sensor_type='temperature'
            ).order_by('-timestamp').first()
            
            latest_humidity = SensorReading.objects.filter(
                sensor_id=sensor.sensor_id,
                sensor_type='humidity'
            ).order_by('-timestamp').first()
            
            sensors_data.append({
                'id': sensor.sensor_id,
                'name': sensor.name,
                'location': sensor.location,
                'is_online': sensor.is_online(),
                'last_seen': sensor.last_seen,
                'temperature': latest_temp.value if latest_temp else None,
                'humidity': latest_humidity.value if latest_humidity else None,
                'temp_timestamp': latest_temp.timestamp if latest_temp else None,
                'humidity_timestamp': latest_humidity.timestamp if latest_humidity else None,
            })
        
        # Estado de calefacción
        heating_control = HeatingControl.objects.filter(
            controller_id='main_heating'
        ).first()
        
        heating_data = None
        if heating_control:
            heating_data = {
                'is_heating': heating_control.is_heating,
                'status': heating_control.status,
                'current_temperature': heating_control.current_temperature,
                'target_temperature': heating_control.target_temperature,
                'is_manual_override': heating_control.is_manual_override_active(),
                'last_updated': heating_control.last_updated,
            }
        
        # Horario actual
        current_schedule = None
        now = timezone.now()
        current_day = now.weekday()
        current_time = now.time()
        
        active_schedule = HeatingSchedule.objects.filter(
            day_of_week=current_day,
            is_active=True,
            start_time__lte=current_time,
            end_time__gte=current_time
        ).order_by('-target_temperature').first()
        
        if active_schedule:
            current_schedule = {
                'name': active_schedule.name,
                'target_temperature': active_schedule.target_temperature,
                'start_time': active_schedule.start_time,
                'end_time': active_schedule.end_time,
            }
        
        return JsonResponse({
            'sensors': sensors_data,
            'heating': heating_data,
            'current_schedule': current_schedule,
            'timestamp': timezone.now(),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
