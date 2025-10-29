from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta, datetime, time
from .models import HeatingSchedule, HeatingControl, HeatingLog, TemperatureThreshold, TemperatureProfile
from .serializers import (
    HeatingScheduleSerializer,
    HeatingControlSerializer,
    HeatingLogSerializer,
    TemperatureThresholdSerializer,
    TemperatureProfileSerializer,
    ManualOverrideSerializer,
    HeatingStatsSerializer,
    ProfileActivationSerializer
)
from .heating_logic import HeatingLogic


class HeatingScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet para horarios de calefacción"""
    queryset = HeatingSchedule.objects.all()
    serializer_class = HeatingScheduleSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro por día de la semana
        day = self.request.query_params.get('day')
        if day is not None:
            queryset = queryset.filter(day_of_week=day)
        
        # Solo horarios activos
        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def current_schedule(self, request):
        """Obtiene el horario activo actual"""
        now = timezone.now()
        current_day = now.weekday()
        current_time = now.time()
        
        schedule = HeatingSchedule.objects.filter(
            day_of_week=current_day,
            is_active=True,
            start_time__lte=current_time,
            end_time__gte=current_time
        ).order_by('-target_temperature').first()
        
        if schedule:
            return Response(HeatingScheduleSerializer(schedule).data)
        
        return Response({'message': 'No hay horario activo'}, status=404)


class HeatingControlViewSet(viewsets.ModelViewSet):
    """ViewSet para control de calefacción"""
    queryset = HeatingControl.objects.all()
    serializer_class = HeatingControlSerializer
    
    @action(detail=True, methods=['post'])
    def manual_override(self, request, pk=None):
        """Activa control manual de la calefacción"""
        control = self.get_object()
        serializer = ManualOverrideSerializer(data=request.data)
        
        if serializer.is_valid():
            turn_on = serializer.validated_data['turn_on']
            duration_hours = serializer.validated_data.get('duration_hours')
            
            heating_logic = HeatingLogic()
            heating_logic.manual_override(control, turn_on, duration_hours)
            
            return Response({'status': 'success', 'message': 'Control manual activado'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def clear_override(self, request, pk=None):
        """Desactiva el control manual"""
        control = self.get_object()
        
        heating_logic = HeatingLogic()
        heating_logic.clear_manual_override(control)
        
        return Response({'status': 'success', 'message': 'Control manual desactivado'})
    
    @action(detail=True, methods=['post'])
    def force_evaluation(self, request, pk=None):
        """Fuerza la evaluación del estado de calefacción"""
        control = self.get_object()
        
        heating_logic = HeatingLogic()
        heating_logic.evaluate_heating_state(control)
        
        control.refresh_from_db()
        return Response(HeatingControlSerializer(control).data)


class HeatingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para logs de calefacción"""
    queryset = HeatingLog.objects.all()
    serializer_class = HeatingLogSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        controller_id = self.request.query_params.get('controller_id')
        action = self.request.query_params.get('action')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if controller_id:
            queryset = queryset.filter(controller_id=controller_id)
        
        if action:
            queryset = queryset.filter(action=action)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtiene estadísticas de uso de calefacción"""
        days = int(request.query_params.get('days', 7))
        controller_id = request.query_params.get('controller_id', 'main_heating')
        
        since = timezone.now() - timedelta(days=days)
        
        # Obtener todos los eventos de encendido y apagado
        logs = HeatingLog.objects.filter(
            controller_id=controller_id,
            timestamp__gte=since,
            action__in=['turn_on', 'turn_off']
        ).order_by('timestamp')
        
        total_runtime_minutes = 0
        total_cycles = 0
        on_time = None
        
        for log in logs:
            if log.action == 'turn_on':
                on_time = log.timestamp
                total_cycles += 1
            elif log.action == 'turn_off' and on_time:
                runtime = (log.timestamp - on_time).total_seconds() / 60
                total_runtime_minutes += runtime
                on_time = None
        
        # Si está actualmente encendido, contar hasta ahora
        if on_time:
            runtime = (timezone.now() - on_time).total_seconds() / 60
            total_runtime_minutes += runtime
        
        total_runtime_hours = total_runtime_minutes / 60
        avg_cycle_duration = total_runtime_minutes / total_cycles if total_cycles > 0 else 0
        
        # Calcular eficiencia (tiempo funcionando vs tiempo total)
        total_hours = days * 24
        efficiency_percent = (total_runtime_hours / total_hours) * 100 if total_hours > 0 else 0
        
        data = {
            'total_runtime_hours': round(total_runtime_hours, 2),
            'total_cycles': total_cycles,
            'avg_cycle_duration': round(avg_cycle_duration, 2),
            'efficiency_percent': round(efficiency_percent, 2),
            'period_start': since,
            'period_end': timezone.now()
        }
        
        serializer = HeatingStatsSerializer(data)
        return Response(serializer.data)


class TemperatureThresholdViewSet(viewsets.ModelViewSet):
    """ViewSet para umbrales de temperatura"""
    queryset = TemperatureThreshold.objects.all()
    serializer_class = TemperatureThresholdSerializer


class TemperatureProfileViewSet(viewsets.ModelViewSet):
    """ViewSet para perfiles de temperatura"""
    queryset = TemperatureProfile.objects.all()
    serializer_class = TemperatureProfileSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro por tipo de perfil
        profile_type = self.request.query_params.get('type')
        if profile_type:
            queryset = queryset.filter(profile_type=profile_type)
        
        # Solo perfiles activos
        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def active_profile(self, request):
        """Obtiene el perfil activo actual"""
        profile = TemperatureProfile.get_active_profile()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def activate_profile(self, request):
        """Activa un perfil específico"""
        serializer = ProfileActivationSerializer(data=request.data)
        
        if serializer.is_valid():
            profile_id = serializer.validated_data['profile_id']
            activate = serializer.validated_data['activate']
            
            try:
                profile = TemperatureProfile.objects.get(id=profile_id)
                
                if activate:
                    # Desactivar otros perfiles
                    TemperatureProfile.objects.update(is_active=False)
                    # Activar el seleccionado
                    profile.is_active = True
                    profile.save()
                    
                    # Log del cambio
                    HeatingLog.objects.create(
                        controller_id='system',
                        action='temperature_change',
                        reason=f'Perfil activado: {profile.name}'
                    )
                    
                    message = f'Perfil "{profile.name}" activado correctamente'
                else:
                    profile.is_active = False
                    profile.save()
                    message = f'Perfil "{profile.name}" desactivado'
                
                return Response({
                    'success': True,
                    'message': message,
                    'profile': TemperatureProfileSerializer(profile).data
                })
                
            except TemperatureProfile.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Perfil no encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def vacation_mode(self, request):
        """Activa/desactiva modo vacaciones"""
        enable = request.query_params.get('enable', 'false').lower() == 'true'
        
        try:
            vacation_profile = TemperatureProfile.objects.get(profile_type='vacation')
            
            if enable:
                # Desactivar otros perfiles y activar vacaciones
                TemperatureProfile.objects.update(is_active=False)
                vacation_profile.is_active = True
                vacation_profile.save()
                
                HeatingLog.objects.create(
                    controller_id='system',
                    action='temperature_change',
                    reason='Modo vacaciones activado'
                )
                
                message = 'Modo vacaciones activado'
            else:
                vacation_profile.is_active = False
                vacation_profile.save()
                
                # Activar perfil normal por defecto
                normal_profile = TemperatureProfile.objects.filter(
                    profile_type='normal', is_default=True
                ).first()
                
                if normal_profile:
                    normal_profile.is_active = True
                    normal_profile.save()
                
                HeatingLog.objects.create(
                    controller_id='system',
                    action='temperature_change',
                    reason='Modo vacaciones desactivado'
                )
                
                message = 'Modo vacaciones desactivado'
            
            return Response({
                'success': True,
                'message': message,
                'vacation_active': enable
            })
            
        except TemperatureProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Perfil de vacaciones no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def current_status(self, request):
        """Estado actual del sistema de perfiles"""
        active_profile = TemperatureProfile.get_active_profile()
        current_time = timezone.now().time()
        
        return Response({
            'active_profile': TemperatureProfileSerializer(active_profile).data,
            'current_target_temperature': active_profile.get_target_temperature(current_time),
            'is_night_time': active_profile.is_night_time(current_time),
            'minimum_protection_temp': active_profile.min_temperature,
            'current_time': current_time.strftime('%H:%M'),
        })
    serializer_class = TemperatureThresholdSerializer
