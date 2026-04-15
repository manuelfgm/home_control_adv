from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
import time

from sensors.models import SensorReading
from actuators.models import ActuatorStatus
from .models import HeatingLog, HeatingDailyUsage, HeatingMonthlyUsage


@login_required
def charts_dashboard_view(request):
    """Vista del dashboard de gráficas"""
    return render(request, 'heating/charts_dashboard.html')


@login_required
def charts_data_api(request):
    """API endpoint para obtener datos de gráficas - OPTIMIZADO"""
    start_time_debug = time.time()
    try:
        period = request.GET.get('period', '24h')
        print(f"[DEBUG] Iniciando charts_data_api para período: {period}")
        
        # Calcular rango de fechas
        now = timezone.now()
        if period == '12h':
            start_time = now - timedelta(hours=12)
        elif period == '24h':
            start_time = now - timedelta(hours=24)
        elif period == '7d':
            start_time = now - timedelta(days=7)
        else:
            start_time = now - timedelta(hours=24)
        
        # Determinar intervalo de muestreo según el período para optimizar rendimiento
        # Reducir puntos en móviles para mejor legibilidad
        is_mobile = request.META.get('HTTP_USER_AGENT', '').lower()
        mobile_detected = any(x in is_mobile for x in ['mobile', 'android', 'iphone', 'ipod'])
        
        if period == '12h':
            # Últimas 12h
            max_points = 120 if mobile_detected else 240
        elif period == '24h':
            # Últimas 24h  
            max_points = 144 if mobile_detected else 288
        elif period == '7d':
            # Últimos 7 días
            max_points = 168 if mobile_detected else 336
        else:
            max_points = 144 if mobile_detected else 288
            
        # Obtener datos de sensores con muestreo optimizado
        # En lugar de obtener todos los registros, obtenemos muestras representativas
        sensor_readings = SensorReading.objects.filter(
            created_at__gte=start_time,
            temperature__isnull=False
        ).order_by('created_at')
        
        # Obtener datos de calefacción desde ActuatorStatus (datos reales del actuador por MQTT)
        heating_logs = ActuatorStatus.objects.filter(
            created_at__gte=start_time
        ).order_by('created_at')
        
        # Procesar datos de sensores con muestreo inteligente
        sensor_data = {
            'labels': [],
            'temperature': [],
            'humidity': [],
            'heating_background': []
        }
        
        # Convertir a lista para procesamiento más eficiente
        sensor_list = list(sensor_readings.values('created_at', 'temperature', 'humidity'))
        # Usar 'created_at' para ActuatorStatus en lugar de 'timestamp'
        heating_list = list(heating_logs.values('created_at', 'is_heating'))
        
        # Debug: añadir información sobre los datos encontrados
        sensor_count = len(sensor_list)
        
        # Crear un diccionario de estado de calefacción por tiempo para búsqueda rápida
        heating_status_by_time = {}
        for log in heating_list:
            heating_status_by_time[log['created_at']] = log['is_heating']
        
        # Generar timeline fijo para mostrar siempre las últimas 24h/12h completas
        now_local = timezone.localtime(now)
        
        # Crear diccionarios para búsqueda rápida de datos por timestamp
        sensors_by_time = {}
        for reading in sensor_list:
            sensors_by_time[reading['created_at']] = reading
            
        # Generar puntos temporales fijos desde ahora hacia atrás
        time_points = []
        if period == '12h':
            # Generar un punto cada 5 minutos para las últimas 12 horas
            for i in range(144):  # 12 * 60 / 5 = 144 puntos
                point_time = now - timedelta(minutes=i * 5)
                time_points.append(point_time)
        elif period == '24h':
            # Generar un punto cada 10 minutos para las últimas 24 horas  
            for i in range(144):  # 24 * 60 / 10 = 144 puntos
                point_time = now - timedelta(minutes=i * 10)
                time_points.append(point_time)
        elif period == '7d':
            # Generar un punto cada 60 minutos para la última semana
            for i in range(168):  # 7 * 24 = 168 puntos
                point_time = now - timedelta(hours=i)
                time_points.append(point_time)
        else:
            # Default: 24h con puntos cada 10 minutos
            for i in range(144):
                point_time = now - timedelta(minutes=i * 10)
                time_points.append(point_time)
        
        # Invertir para que vaya de más antiguo a más reciente
        time_points.reverse()
        
        # Debug: información sobre timeline
        print(f"Generando timeline fijo de {len(time_points)} puntos para período {period}")
        
        # Procesar cada punto temporal fijo
        for point_time in time_points:
            point_time_local = timezone.localtime(point_time)
            
            # Formatear etiqueta según el período
            if period == '12h' or period == '24h':
                label = point_time_local.strftime('%H:%M')
            elif period == '7d':
                label = point_time_local.strftime('%d/%m %H:%M')
            else:
                label = point_time_local.strftime('%H:%M')
                
            sensor_data['labels'].append(label)
            
            # Buscar el dato de sensor más cercano a este punto temporal
            closest_sensor = None
            min_diff = float('inf')
            
            for sensor_time, sensor_reading in sensors_by_time.items():
                diff = abs((point_time - sensor_time).total_seconds())
                if diff < min_diff and diff < 3600:  # Máximo 1 hora de tolerancia
                    min_diff = diff
                    closest_sensor = sensor_reading
            
            # Agregar datos de sensor (usar null para JSON válido)
            if closest_sensor:
                sensor_data['temperature'].append(closest_sensor['temperature'])
                sensor_data['humidity'].append(closest_sensor['humidity'] or 0)
            else:
                # Usar null para JSON válido (Chart.js maneja null correctamente)
                sensor_data['temperature'].append(None)
                sensor_data['humidity'].append(None)
            
            # Buscar estado de calefacción más cercano
            closest_heating = None
            if heating_status_by_time:
                closest_time = min(heating_status_by_time.keys(), 
                                 key=lambda x: abs((point_time - x).total_seconds()),
                                 default=None)
                
                if closest_time:
                    diff = abs((point_time - closest_time).total_seconds())
                    if diff < 3600:  # 1 hora de tolerancia
                        closest_heating = heating_status_by_time[closest_time]
            
            # Agregar valor para fondo de calefacción
            sensor_data['heating_background'].append(30 if closest_heating else 0)

        # Debug: verificar datos generados
        non_null_temps = [t for t in sensor_data['temperature'] if t is not None]
        print(f"[DEBUG] Generados {len(sensor_data['labels'])} puntos temporales, {len(non_null_temps)} con datos de temperatura")
        
        # Si no hay datos reales, generar algunos datos de ejemplo para mostrar la gráfica
        if len(non_null_temps) == 0:
            print("[DEBUG] No hay datos reales, generando datos de ejemplo")
            # Reemplazar algunos valores None con datos de ejemplo
            for i in range(0, len(sensor_data['temperature']), max(1, len(sensor_data['temperature']) // 10)):
                sensor_data['temperature'][i] = 20.0 + (i % 5) * 0.5
                sensor_data['humidity'][i] = 50.0 + (i % 3) * 5
        
        # Uso diario — una sola consulta a la tabla pre-calculada
        daily_data = {
            'labels': [],
            'hours': []
        }

        now_local = timezone.localtime(now)
        thirty_days_ago = now_local.date() - timedelta(days=29)

        daily_usage_map = {
            u.date: u.total_hours
            for u in HeatingDailyUsage.objects.filter(date__gte=thirty_days_ago)
        }

        for i in range(29, -1, -1):
            day_date = now_local.date() - timedelta(days=i)
            daily_data['labels'].append(day_date.strftime('%d/%m'))
            daily_data['hours'].append(round(daily_usage_map.get(day_date, 0.0), 1))

        # Uso mensual — una sola consulta a la tabla pre-calculada
        monthly_data = {
            'labels': [],
            'hours': []
        }

        # Calcular los 12 pares (año, mes) en orden ascendente
        y, m = now_local.year, now_local.month
        months_needed = []
        for _ in range(12):
            months_needed.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        months_needed.reverse()  # de más antiguo a más reciente

        years_needed = list({yr for yr, _ in months_needed})
        monthly_usage_map = {
            (u.year, u.month): u.total_hours
            for u in HeatingMonthlyUsage.objects.filter(year__in=years_needed)
        }

        for yr, mo in months_needed:
            month_name = calendar.month_name[mo][:3]
            monthly_data['labels'].append(f"{month_name} {yr}")
            monthly_data['hours'].append(round(monthly_usage_map.get((yr, mo), 0.0), 1))
        
        # Obtener estadísticas actuales (optimizado)
        current_sensor = SensorReading.objects.filter(
            temperature__isnull=False
        ).order_by('-created_at').first()
        
        current_heating = HeatingLog.objects.order_by('-timestamp').first()
        
        current_stats = {
            'temperature': current_sensor.temperature if current_sensor else None,
            'humidity': current_sensor.humidity if current_sensor else None,
            'is_heating': current_heating.is_heating if current_heating else False,
            'target_temperature': current_heating.target_temperature if current_heating else None,
        }
        
        end_time_debug = time.time()
        processing_time = round(end_time_debug - start_time_debug, 2)
        print(f"[DEBUG] charts_data_api completado en {processing_time}s para período {period}")
        
        return JsonResponse({
            'sensor_data': sensor_data,
            'daily_usage': daily_data,
            'monthly_usage': monthly_data,
            'current_stats': current_stats,
            'period': period,
            'debug_info': {
                'processing_time': processing_time,
                'total_sensor_records': sensor_count,
                'generated_timeline_points': len(sensor_data['labels']),
                'non_null_temperatures': len([t for t in sensor_data['temperature'] if t is not None]),
                'non_null_humidity': len([h for h in sensor_data['humidity'] if h is not None]),
                'heating_logs_count': len(heating_list),
                'period_requested': period
            }
        })
        
    except Exception as e:
        print(f"[ERROR] charts_data_api falló: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def calculate_heating_time_from_dict_list(logs_dict_list):
    """
    Versión optimizada que calcula tiempo directamente desde lista de diccionarios
    Adaptado para trabajar con ActuatorStatus (usa 'created_at' en lugar de 'timestamp')
    """
    if not logs_dict_list:
        return 0.0
    
    total_seconds = 0.0
    heating_start = None
    
    for log in logs_dict_list:
        # Usar 'created_at' si existe, sino 'timestamp' para retrocompatibilidad
        log_time = log.get('created_at') or log.get('timestamp')
        
        if log['is_heating'] and heating_start is None:
            # Comienza un período de calefacción
            heating_start = log_time
        elif not log['is_heating'] and heating_start is not None:
            # Termina un período de calefacción
            heating_end = log_time
            period_seconds = (heating_end - heating_start).total_seconds()
            total_seconds += period_seconds
            heating_start = None
    
    # Si la calefacción seguía encendida al final del período
    if heating_start is not None and logs_dict_list:
        # Asumir que sigue encendida hasta el último log
        last_log_time = logs_dict_list[-1].get('created_at') or logs_dict_list[-1].get('timestamp')
        period_seconds = (last_log_time - heating_start).total_seconds()
        total_seconds += period_seconds
    
    return total_seconds / 3600.0  # Convertir a horas

def calculate_real_heating_time(logs_queryset):
    """
    Calcula el tiempo real que la calefacción estuvo encendida
    basándose en los períodos entre logs de ON y OFF
    Adaptado para trabajar con ActuatorStatus (usa 'created_at' en lugar de 'timestamp')
    """
    # Detectar si es ActuatorStatus o HeatingLog
    model_name = logs_queryset.model.__name__ if hasattr(logs_queryset, 'model') else None
    time_field = 'created_at' if model_name == 'ActuatorStatus' else 'timestamp'
    
    logs = list(logs_queryset.values(time_field, 'is_heating').order_by(time_field))
    
    if not logs:
        return 0.0
    
    total_seconds = 0.0
    heating_start = None
    
    for log in logs:
        log_time = log[time_field]
        
        if log['is_heating'] and heating_start is None:
            # Comienza un período de calefacción
            heating_start = log_time
        elif not log['is_heating'] and heating_start is not None:
            # Termina un período de calefacción
            heating_end = log_time
            period_seconds = (heating_end - heating_start).total_seconds()
            total_seconds += period_seconds
            heating_start = None
    
    # Si la calefacción seguía encendida al final del período
    if heating_start is not None and logs:
        # Asumir que sigue encendida hasta el último log
        last_log_time = logs[-1][time_field]
        period_seconds = (last_log_time - heating_start).total_seconds()
        total_seconds += period_seconds
    
    return total_seconds / 3600.0  # Convertir a horas