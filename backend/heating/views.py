from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db import models
from .models import HeatingSettings, HeatingSchedule, HeatingLog
from .serializers import (
    HeatingSettingsSerializer, HeatingScheduleSerializer, 
    HeatingLogSerializer, CurrentStatusSerializer
)


class HeatingSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuración de calefacción
    """
    queryset = HeatingSettings.objects.all()
    serializer_class = HeatingSettingsSerializer
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener configuración actual activa"""
        settings = HeatingSettings.get_current_settings()
        if settings:
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'No hay configuración activa'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activar una configuración específica"""
        try:
            # Desactivar todas las configuraciones
            HeatingSettings.objects.all().update(is_active=False)
            
            # Activar la seleccionada
            settings = self.get_object()
            settings.is_active = True
            settings.save()
            
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class HeatingScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para horarios de calefacción
    """
    queryset = HeatingSchedule.objects.all()
    serializer_class = HeatingScheduleSerializer
    
    def get_queryset(self):
        """Filtrar por configuración si se especifica"""
        queryset = super().get_queryset()
        settings_id = self.request.query_params.get('settings_id')
        if settings_id:
            queryset = queryset.filter(settings_id=settings_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def current_active(self, request):
        """Obtener horario activo actual"""
        active_schedule = HeatingSchedule.get_current_active_schedule()
        if active_schedule:
            serializer = self.get_serializer(active_schedule)
            return Response(serializer.data)
        else:
            return Response(
                {'message': 'No hay horario activo en este momento'}, 
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['get'])
    def by_day(self, request):
        """Obtener horarios agrupados por día"""
        schedules_by_day = {}
        
        # Inicializar todos los días
        for day_num, day_name in HeatingSchedule.WEEKDAYS:
            schedules_by_day[day_name] = []
        
        # Obtener todos los horarios activos
        all_schedules = self.get_queryset().filter(is_active=True)
        
        # Agrupar horarios por día
        for schedule in all_schedules:
            weekdays_list = schedule.get_weekdays_list()
            schedule_data = self.get_serializer(schedule).data
            
            # Agregar este horario a todos los días que le corresponden
            for day_num in weekdays_list:
                if 0 <= day_num <= 6:
                    day_name = dict(HeatingSchedule.WEEKDAYS)[day_num]
                    schedules_by_day[day_name].append(schedule_data)
        
        return Response(schedules_by_day)


class HeatingLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet para logs de calefacción
    """
    queryset = HeatingLog.objects.all()
    serializer_class = HeatingLogSerializer
    
    def get_queryset(self):
        """Filtrar logs por fecha si se especifica"""
        queryset = super().get_queryset()
        
        # Filtro por fecha
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Obtener el último log"""
        latest = self.get_queryset().first()
        if latest:
            serializer = self.get_serializer(latest)
            return Response(serializer.data)
        else:
            return Response(
                {'message': 'No hay logs disponibles'}, 
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas de calefacción"""
        today = timezone.now().date()
        
        # Logs de hoy
        today_logs = self.get_queryset().filter(timestamp__date=today)
        
        # Tiempo encendido hoy
        heating_logs = today_logs.filter(is_heating=True)
        
        stats = {
            'today_total_logs': today_logs.count(),
            'today_heating_logs': heating_logs.count(),
            'average_temperature': today_logs.aggregate(
                avg_temp=models.Avg('current_temperature')
            )['avg_temp'],
            'max_temperature': today_logs.aggregate(
                max_temp=models.Max('current_temperature')
            )['max_temp'],
            'min_temperature': today_logs.aggregate(
                min_temp=models.Min('current_temperature')
            )['min_temp'],
        }
        
        return Response(stats)


class HeatingControlViewSet(viewsets.ViewSet):
    """
    ViewSet para control general del sistema de calefacción
    """
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Obtener estado actual completo del sistema"""
        serializer = CurrentStatusSerializer()
        return Response(serializer.to_representation(None))
    
    @action(detail=False, methods=['get'])
    def target_temperature(self, request):
        """Obtener temperatura objetivo actual"""
        target_temp = HeatingSchedule.get_current_target_temperature()
        active_schedule = HeatingSchedule.get_current_active_schedule()
        
        return Response({
            'target_temperature': target_temp,
            'source': 'schedule' if active_schedule else 'default',
            'active_schedule': HeatingScheduleSerializer(active_schedule).data if active_schedule else None
        })
    
    @action(detail=False, methods=['post'])
    def manual_override(self, request):
        """Control manual temporal"""
        temperature = request.data.get('temperature')
        duration_minutes = request.data.get('duration_minutes', 60)
        
        if not temperature:
            return Response(
                {'error': 'temperature is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear log de control manual
        HeatingLog.objects.create(
            is_heating=True,  # Asumimos que se enciende
            target_temperature=temperature,
            action_reason=f'manual_override_{duration_minutes}min',
            source='manual_control'
        )
        
        return Response({
            'message': f'Override manual activado por {duration_minutes} minutos',
            'temperature': temperature,
            'duration_minutes': duration_minutes
        })
    
    @action(detail=False, methods=['post'])
    def test_mqtt(self, request):
        """Probar envío de comando MQTT"""
        try:
            from .models import MQTTService
            
            temperature = request.data.get('temperature', 20.0)
            action = request.data.get('action', 'turn_on')  # turn_on o turn_off
            actuator_id = request.data.get('actuator_id', 'boiler')
            
            mqtt_service = MQTTService()
            result = mqtt_service.send_actuator_command(actuator_id, temperature, action)
            
            return Response({
                'success': result,
                'message': 'Comando MQTT enviado' if result else 'Error enviando comando MQTT',
                'command': {
                    'actuator_id': actuator_id,
                    'temperature': temperature,
                    'action': action
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error enviando comando MQTT: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
