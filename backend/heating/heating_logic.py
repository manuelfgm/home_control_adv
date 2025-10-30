import logging
from datetime import datetime, time
from django.utils import timezone
from django.db.models import Q
from .models import HeatingSchedule, HeatingControl, HeatingLog, HeatingSettings

logger = logging.getLogger(__name__)


class HeatingLogic:
    """Lógica de control de calefacción"""
    
    def __init__(self):
        self.hysteresis = 0.5  # Histéresis por defecto
    
    def evaluate_heating_state(self, control):
        """Evalúa si la calefacción debe estar encendida o apagada"""
        try:
            current_time = timezone.now()
            current_temperature = control.current_temperature
            
            if current_temperature is None:
                logger.warning("No hay temperatura actual disponible")
                return
            
            # Obtener configuración del sistema
            settings = HeatingSettings.get_settings()
            
            # Verificar si hay un horario activo
            scheduled_temp = self.get_current_target_temperature()
            
            # Determinar temperatura objetivo
            if scheduled_temp is not None:
                # Hay un horario activo, usar esa temperatura
                target_temp = max(scheduled_temp, settings.minimum_temperature)
                reason_prefix = "Horario programado"
            else:
                # No hay horario activo, usar temperatura mínima configurada
                target_temp = settings.minimum_temperature
                reason_prefix = "Temperatura mínima"
            
            control.target_temperature = target_temp
            control.save()
            
            # Aplicar lógica de histéresis
            should_heat = self.should_turn_on_heating(current_temperature, target_temp, control.is_heating)
            
            if should_heat and not control.is_heating:
                reason = f"{reason_prefix}: {current_temperature}°C < objetivo {target_temp}°C"
                self.turn_on_heating(control, reason)
            elif not should_heat and control.is_heating:
                reason = f"{reason_prefix}: {current_temperature}°C >= objetivo {target_temp}°C"
                self.turn_off_heating(control, reason)
                
        except Exception as e:
            logger.error(f"Error evaluando estado de calefacción: {e}")
    
    def get_current_target_temperature(self):
        """Obtiene la temperatura objetivo para el momento actual"""
        # Usar el método del modelo que maneja múltiples días
        active_schedule = HeatingSchedule.get_current_active_schedule()
        
        if active_schedule:
            return active_schedule.target_temperature
        
        return None
    
    def should_turn_on_heating(self, current_temp, target_temp, currently_heating):
        """Determina si se debe encender la calefacción usando histéresis"""
        settings = HeatingSettings.get_settings()
        hysteresis = settings.hysteresis
        
        if currently_heating:
            # Si ya está calentando, mantener hasta alcanzar temperatura objetivo
            return current_temp < target_temp
        else:
            # Si no está calentando, encender si está por debajo de objetivo - histéresis
            return current_temp < (target_temp - hysteresis)
    
    def turn_on_heating(self, control, reason=""):
        """Enciende la calefacción"""
        try:
            if not control.is_heating:
                control.is_heating = True
                control.save()
                
                # Registrar en el log
                HeatingLog.objects.create(
                    controller_id=control.controller_id,
                    action='turn_on',
                    temperature_before=control.current_temperature,
                    target_temperature=control.target_temperature,
                    reason=reason
                )
                
                # Enviar comando MQTT
                from sensors.mqtt_client import mqtt_client
                mqtt_client.publish_heating_command('ON', control.controller_id)
                
                logger.info(f"Calefacción encendida: {reason}")
                
        except Exception as e:
            logger.error(f"Error encendiendo calefacción: {e}")
    
    def turn_off_heating(self, control, reason=""):
        """Apaga la calefacción"""
        try:
            if control.is_heating:
                # Calcular duración
                last_on = HeatingLog.objects.filter(
                    controller_id=control.controller_id,
                    action='turn_on'
                ).order_by('-timestamp').first()
                
                duration_minutes = None
                if last_on:
                    duration = timezone.now() - last_on.timestamp
                    duration_minutes = int(duration.total_seconds() / 60)
                
                control.is_heating = False
                control.save()
                
                # Registrar en el log
                HeatingLog.objects.create(
                    controller_id=control.controller_id,
                    action='turn_off',
                    temperature_before=control.current_temperature,
                    target_temperature=control.target_temperature,
                    reason=reason,
                    duration_minutes=duration_minutes
                )
                
                # Enviar comando MQTT
                from sensors.mqtt_client import mqtt_client
                mqtt_client.publish_heating_command('OFF', control.controller_id)
                
                logger.info(f"Calefacción apagada: {reason}")
                
        except Exception as e:
            logger.error(f"Error apagando calefacción: {e}")
    
    def manual_override(self, control, turn_on, duration_hours=None):
        """Activa override manual de la calefacción"""
        try:
            control.manual_override = True
            
            if duration_hours:
                control.manual_override_until = timezone.now() + timezone.timedelta(hours=duration_hours)
            else:
                control.manual_override_until = None
            
            if turn_on:
                control.is_heating = True
                action = 'turn_on'
                reason = f"Override manual - Encendido por {duration_hours or 'indefinido'} horas"
            else:
                control.is_heating = False
                action = 'turn_off'
                reason = f"Override manual - Apagado por {duration_hours or 'indefinido'} horas"
            
            control.save()
            
            # Registrar en el log
            HeatingLog.objects.create(
                controller_id=control.controller_id,
                action=action,
                temperature_before=control.current_temperature,
                target_temperature=control.target_temperature,
                reason=reason
            )
            
            # Enviar comando MQTT
            from sensors.mqtt_client import mqtt_client
            command = 'ON' if turn_on else 'OFF'
            mqtt_client.publish_heating_command(command, control.controller_id)
            
            logger.info(f"Override manual activado: {reason}")
            
        except Exception as e:
            logger.error(f"Error en override manual: {e}")
    
    def clear_manual_override(self, control):
        """Desactiva el override manual"""
        try:
            control.manual_override = False
            control.manual_override_until = None
            control.save()
            
            HeatingLog.objects.create(
                controller_id=control.controller_id,
                action='manual_override',
                reason="Override manual desactivado"
            )
            
            # Reevaluar estado basado en horarios
            self.evaluate_heating_state(control)
            
            logger.info("Override manual desactivado")
            
        except Exception as e:
            logger.error(f"Error desactivando override manual: {e}")