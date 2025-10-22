from django.core.management.base import BaseCommand
from django.utils import timezone
from heating.models import HeatingControl
from heating.heating_logic import HeatingLogic
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Evalúa los horarios de calefacción y actualiza el estado automáticamente'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--controller-id',
            type=str,
            default='main_heating',
            help='ID del controlador a evaluar (por defecto: main_heating)'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada del proceso'
        )
    
    def handle(self, *args, **options):
        controller_id = options['controller_id']
        verbose = options['verbose']
        
        try:
            # Obtener el controlador
            try:
                control = HeatingControl.objects.get(controller_id=controller_id)
            except HeatingControl.DoesNotExist:
                # Crear controlador si no existe
                control = HeatingControl.objects.create(
                    controller_id=controller_id,
                    name=f'Calefacción {controller_id}',
                    status='auto'
                )
                self.stdout.write(
                    self.style.WARNING(f'Controlador {controller_id} creado automáticamente')
                )
            
            if verbose:
                self.stdout.write(f'📊 Estado actual del controlador {controller_id}:')
                self.stdout.write(f'  Estado: {control.get_status_display()}')
                self.stdout.write(f'  Calentando: {"Sí" if control.is_heating else "No"}')
                self.stdout.write(f'  Temperatura actual: {control.current_temperature}°C')
                self.stdout.write(f'  Temperatura objetivo: {control.target_temperature}°C')
                self.stdout.write(f'  Override manual: {"Activo" if control.is_manual_override_active() else "Inactivo"}')
            
            # Solo evaluar si está en modo automático y no hay override manual
            if control.status != 'auto':
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Controlador no está en modo automático (modo: {control.status})')
                    )
                return
            
            if control.is_manual_override_active():
                if verbose:
                    self.stdout.write(
                        self.style.WARNING('⚠️  Override manual activo, saltando evaluación automática')
                    )
                return
            
            # Evaluar estado
            heating_logic = HeatingLogic()
            previous_state = control.is_heating
            
            heating_logic.evaluate_heating_state(control)
            
            # Recargar el objeto para obtener el estado actualizado
            control.refresh_from_db()
            
            # Mostrar resultado
            if control.is_heating != previous_state:
                action = "🔥 ENCENDIDA" if control.is_heating else "❄️  APAGADA"
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Calefacción {action}')
                )
                
                if verbose:
                    target = heating_logic.get_current_target_temperature()
                    if target:
                        self.stdout.write(f'  Temperatura objetivo actual: {target}°C')
                    else:
                        self.stdout.write('  No hay horario activo')
                
                logger.info(f'Heating state changed: {previous_state} -> {control.is_heating}')
            else:
                if verbose:
                    self.stdout.write('ℹ️  Sin cambios en el estado de calefacción')
            
            # Mostrar información del horario actual
            if verbose:
                target_temp = heating_logic.get_current_target_temperature()
                if target_temp:
                    self.stdout.write(f'🎯 Temperatura objetivo activa: {target_temp}°C')
                else:
                    self.stdout.write('⏰ No hay horario activo en este momento')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error evaluando horarios: {e}')
            )
            logger.error(f'Error in evaluate_heating: {e}')
            raise