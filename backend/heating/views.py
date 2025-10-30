from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta, datetime, time
from .models import HeatingSchedule, HeatingControl, HeatingLog, HeatingSettings
from .serializers import (
    HeatingScheduleSerializer,
    HeatingControlSerializer,
    HeatingLogSerializer,
    HeatingSettingsSerializer,
    ManualOverrideSerializer,
    HeatingStatsSerializer
)
from .heating_logic import HeatingLogic


def dashboard(request):
    """Vista principal del dashboard de calefacción"""
    context = {
        'active_schedules': HeatingSchedule.objects.filter(is_active=True).order_by('start_time'),
        'heating_control': HeatingControl.objects.first() or HeatingControl.objects.create(),
        'recent_logs': HeatingLog.objects.all()[:10],
        'settings': HeatingSettings.get_settings(),
    }
    return render(request, 'dashboard/index.html', context)


class HeatingScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar horarios de calefacción"""
    
    queryset = HeatingSchedule.objects.all()
    serializer_class = HeatingScheduleSerializer
    
    def get_queryset(self):
        """Filtrar por estado activo si se solicita"""
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        return queryset.order_by('start_time')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Obtener horarios activos"""
        active_schedules = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener el horario activo actual"""
        current_schedule = HeatingSchedule.get_current_active_schedule()
        
        if current_schedule:
            serializer = self.get_serializer(current_schedule)
            return Response({
                'has_active_schedule': True,
                'schedule': serializer.data,
                'target_temperature': current_schedule.target_temperature
            })
        else:
            settings = HeatingSettings.get_settings()
            return Response({
                'has_active_schedule': False,
                'schedule': None,
                'target_temperature': settings.minimum_temperature
            })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar un horario"""
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save()
        
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)


class HeatingControlViewSet(viewsets.ModelViewSet):
    """ViewSet para control de calefacción"""
    
    queryset = HeatingControl.objects.all()
    serializer_class = HeatingControlSerializer
    
    @action(detail=True, methods=['post'])
    def manual_override(self, request, pk=None):
        """Control manual de la calefacción"""
        control = self.get_object()
        serializer = ManualOverrideSerializer(data=request.data)
        
        if serializer.is_valid():
            turn_on = serializer.validated_data['turn_on']
            duration_hours = serializer.validated_data.get('duration_hours')
            
            logic = HeatingLogic()
            logic.manual_override(control, turn_on, duration_hours)
            
            # Actualizar el estado
            control.refresh_from_db()
            response_serializer = self.get_serializer(control)
            
            return Response({
                'message': 'Override manual activado',
                'control': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def clear_override(self, request, pk=None):
        """Limpiar override manual"""
        control = self.get_object()
        
        logic = HeatingLogic()
        logic.clear_manual_override(control)
        
        control.refresh_from_db()
        serializer = self.get_serializer(control)
        
        return Response({
            'message': 'Override manual desactivado',
            'control': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Obtener estado completo del sistema"""
        control = HeatingControl.objects.first()
        if not control:
            control = HeatingControl.objects.create()
        
        current_schedule = HeatingSchedule.get_current_active_schedule()
        settings = HeatingSettings.get_settings()
        
        # Determinar temperatura objetivo
        if current_schedule:
            target_temp = current_schedule.target_temperature
            heating_reason = f"Horario: {current_schedule.name}"
        else:
            target_temp = settings.minimum_temperature
            heating_reason = "Temperatura mínima"
        
        return Response({
            'control': HeatingControlSerializer(control).data,
            'current_schedule': HeatingScheduleSerializer(current_schedule).data if current_schedule else None,
            'settings': HeatingSettingsSerializer(settings).data,
            'target_temperature': target_temp,
            'heating_reason': heating_reason,
            'has_manual_override': control.is_manual_override_active(),
        })


class HeatingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para logs de calefacción (solo lectura)"""
    
    queryset = HeatingLog.objects.all()
    serializer_class = HeatingLogSerializer
    
    def get_queryset(self):
        """Filtrar logs por fecha y acción"""
        queryset = super().get_queryset()
        
        # Filtrar por fecha
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # Filtrar por acción
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas de calefacción"""
        # Parámetros de período
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        end_date = timezone.now()
        
        # Logs del período
        logs = self.get_queryset().filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        # Calcular estadísticas
        turn_on_logs = logs.filter(action='turn_on')
        turn_off_logs = logs.filter(action='turn_off')
        
        total_cycles = turn_on_logs.count()
        total_runtime = turn_off_logs.aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        
        avg_cycle_duration = total_runtime / total_cycles if total_cycles > 0 else 0
        total_runtime_hours = total_runtime / 60
        
        # Eficiencia aproximada (tiempo encendido vs tiempo total)
        total_period_hours = (end_date - start_date).total_seconds() / 3600
        efficiency_percent = (total_runtime_hours / total_period_hours * 100) if total_period_hours > 0 else 0
        
        stats_data = {
            'total_runtime_hours': round(total_runtime_hours, 2),
            'total_cycles': total_cycles,
            'avg_cycle_duration': round(avg_cycle_duration, 1),
            'efficiency_percent': round(efficiency_percent, 1),
            'period_start': start_date,
            'period_end': end_date
        }
        
        serializer = HeatingStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Logs recientes"""
        limit = int(request.query_params.get('limit', 20))
        recent_logs = self.get_queryset()[:limit]
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)


class HeatingSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet para configuración de calefacción"""
    
    queryset = HeatingSettings.objects.all()
    serializer_class = HeatingSettingsSerializer
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener configuración actual"""
        settings = HeatingSettings.get_settings()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update_minimum_temperature(self, request):
        """Actualizar solo la temperatura mínima"""
        settings = HeatingSettings.get_settings()
        new_temp = request.data.get('minimum_temperature')
        
        if new_temp is not None:
            try:
                new_temp = float(new_temp)
                if 5 <= new_temp <= 25:
                    settings.minimum_temperature = new_temp
                    settings.save()
                    
                    serializer = self.get_serializer(settings)
                    return Response({
                        'message': f'Temperatura mínima actualizada a {new_temp}°C',
                        'settings': serializer.data
                    })
                else:
                    return Response({
                        'error': 'La temperatura debe estar entre 5°C y 25°C'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Temperatura inválida'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'error': 'Temperatura mínima requerida'
        }, status=status.HTTP_400_BAD_REQUEST)


# Vista para el template de configuración
def settings_view(request):
    """Vista para la página de configuración"""
    context = {
        'settings': HeatingSettings.get_settings(),
        'schedules': HeatingSchedule.objects.filter(is_active=True).order_by('start_time'),
    }
    return render(request, 'dashboard/settings.html', context)