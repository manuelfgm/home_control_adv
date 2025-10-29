from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from sensors.models import SensorReading, SensorStatus
from heating.models import HeatingControl, HeatingSchedule, HeatingLog
from datetime import timedelta
from django.utils import timezone
import json


class DashboardView(LoginRequiredMixin, TemplateView):
    """Vista principal del dashboard - Solo sirve template estático"""
    template_name = 'dashboard/index.html'
    login_url = '/admin/login/'


class SchedulesView(LoginRequiredMixin, TemplateView):
    """Vista para configuración de horarios - Solo sirve template estático"""
    template_name = 'dashboard/schedules.html'
    login_url = '/admin/login/'


class HistoryView(LoginRequiredMixin, TemplateView):
    """Vista para histórico de datos - Solo sirve template estático"""
    template_name = 'dashboard/history.html'
    login_url = '/admin/login/'


class ControlView(LoginRequiredMixin, TemplateView):
    """Vista para control manual - Solo sirve template estático"""
    template_name = 'dashboard/control.html'
    login_url = '/admin/login/'


class ProfilesView(LoginRequiredMixin, TemplateView):
    """Vista para perfiles de temperatura - Solo sirve template estático"""
    template_name = 'dashboard/profiles.html'
    login_url = '/admin/login/'


# =================
# API ENDPOINTS
# =================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
        
        # Horario actual usando el nuevo método
        active_schedule = HeatingSchedule.get_current_active_schedule()
        
        current_schedule = None
        if active_schedule:
            current_schedule = {
                'id': active_schedule.id,
                'name': active_schedule.name,
                'target_temperature': active_schedule.target_temperature,
                'start_time': active_schedule.start_time,
                'end_time': active_schedule.end_time,
                'active_days': active_schedule.get_active_days(),
                'active_days_display': active_schedule.get_active_days_display(),
            }
        
        return Response({
            'sensors': sensors_data,
            'heating': heating_data,
            'current_schedule': current_schedule,
            'timestamp': timezone.now(),
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api_history_stats(request):
    """API endpoint para estadísticas históricas"""
    try:
        # Parámetros opcionales
        days = int(request.GET.get('days', 7))
        
        # Fecha límite
        date_limit = timezone.now() - timedelta(days=days)
        
        # Conteo de logs de calefacción
        heating_logs_count = HeatingLog.objects.filter(
            timestamp__gte=date_limit
        ).count()
        
        # Conteo de lecturas de temperatura
        temperature_readings_count = SensorReading.objects.filter(
            sensor_type='temperature',
            timestamp__gte=date_limit
        ).count()
        
        # Tiempo total de calefacción encendida
        heating_on_logs = HeatingLog.objects.filter(
            timestamp__gte=date_limit,
            action='turn_on'
        ).count()
        
        # Temperatura promedio
        from django.db.models import Avg
        avg_temp = SensorReading.objects.filter(
            sensor_type='temperature',
            timestamp__gte=date_limit
        ).aggregate(avg_temp=Avg('value'))['avg_temp']
        
        return Response({
            'period_days': days,
            'heating_logs_count': heating_logs_count,
            'temperature_readings_count': temperature_readings_count,
            'heating_activations': heating_on_logs,
            'average_temperature': round(avg_temp, 2) if avg_temp else None,
            'date_from': date_limit,
            'date_to': timezone.now(),
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api_temperature_chart(request):
    """API endpoint para datos del gráfico de temperatura"""
    try:
        # Parámetros
        hours = int(request.GET.get('hours', 24))
        sensor_id = request.GET.get('sensor_id', 'room_sensor')
        
        # Fecha límite
        date_limit = timezone.now() - timedelta(hours=hours)
        
        # Lecturas de temperatura
        temperature_readings = SensorReading.objects.filter(
            sensor_id=sensor_id,
            sensor_type='temperature',
            timestamp__gte=date_limit
        ).order_by('timestamp').values('timestamp', 'value')
        
        # Convertir a formato para Chart.js
        chart_data = {
            'labels': [],
            'datasets': [{
                'label': 'Temperatura (°C)',
                'data': [],
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.1)',
                'tension': 0.1
            }]
        }
        
        for reading in temperature_readings:
            chart_data['labels'].append(reading['timestamp'].strftime('%H:%M'))
            chart_data['datasets'][0]['data'].append(reading['value'])
        
        return Response(chart_data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api_schedules(request):
    """API endpoint para obtener todos los horarios"""
    try:
        schedules = HeatingSchedule.objects.all().order_by('start_time')
        
        schedules_data = []
        for schedule in schedules:
            schedules_data.append({
                'id': schedule.id,
                'name': schedule.name,
                # Campos de múltiples días
                'monday': schedule.monday,
                'tuesday': schedule.tuesday,
                'wednesday': schedule.wednesday,
                'thursday': schedule.thursday,
                'friday': schedule.friday,
                'saturday': schedule.saturday,
                'sunday': schedule.sunday,
                # Compatibilidad
                'day_of_week': schedule.day_of_week,
                'day_name': schedule.get_day_of_week_display() if schedule.day_of_week is not None else None,
                # Información de días activos
                'active_days': schedule.get_active_days(),
                'active_days_display': schedule.get_active_days_display(),
                # Otros campos
                'start_time': schedule.start_time,
                'end_time': schedule.end_time,
                'target_temperature': schedule.target_temperature,
                'is_active': schedule.is_active,
                'created_at': schedule.created_at,
                'updated_at': schedule.updated_at,
            })
        
        return Response({'schedules': schedules_data})
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dashboard_api_manual_control(request):
    """API endpoint para control manual de calefacción"""
    try:
        action = request.data.get('action')  # 'turn_on', 'turn_off', 'set_temperature'
        temperature = request.data.get('temperature')
        duration_minutes = request.data.get('duration_minutes', 60)
        
        heating_control = HeatingControl.objects.filter(
            controller_id='main_heating'
        ).first()
        
        if not heating_control:
            # Crear control si no existe
            heating_control = HeatingControl.objects.create(
                controller_id='main_heating',
                is_heating=False,
                status='manual_control'
            )
        
        if action == 'turn_on':
            heating_control.is_heating = True
            heating_control.status = 'manual_on'
            heating_control.manual_override_until = timezone.now() + timedelta(minutes=duration_minutes)
            
        elif action == 'turn_off':
            heating_control.is_heating = False
            heating_control.status = 'manual_off'
            heating_control.manual_override_until = timezone.now() + timedelta(minutes=duration_minutes)
            
        elif action == 'set_temperature' and temperature:
            heating_control.target_temperature = temperature
            heating_control.status = 'manual_temp'
            heating_control.manual_override_until = timezone.now() + timedelta(minutes=duration_minutes)
            
        elif action == 'clear_override':
            heating_control.manual_override_until = None
            heating_control.status = 'auto'
            
        else:
            return Response({'error': 'Acción no válida'}, status=400)
        
        heating_control.last_updated = timezone.now()
        heating_control.save()
        
        # Registrar acción
        HeatingLog.objects.create(
            controller_id='main_heating',
            action=action,
            temperature=temperature,
            reason=f'Manual control by {request.user.username}'
        )
        
        return Response({'success': True, 'message': f'Acción {action} ejecutada correctamente'})
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)
