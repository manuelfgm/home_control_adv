from django.core.management.base import BaseCommand
from sensors.mqtt_client import mqtt_client
import logging
import signal
import sys

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Inicia el cliente MQTT para recibir datos de sensores y enviar comandos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reconnect-interval',
            type=int,
            default=5,
            help='Intervalo de reconexión en segundos (por defecto: 5)'
        )
    
    def handle(self, *args, **options):
        reconnect_interval = options['reconnect_interval']
        
        # Configurar manejo de señales para cierre limpio
        def signal_handler(sig, frame):
            self.stdout.write('\n🛑 Recibida señal de interrupción, cerrando cliente MQTT...')
            mqtt_client.disconnect()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.stdout.write('🚀 Iniciando cliente MQTT...')
        
        try:
            # Conectar al broker MQTT
            mqtt_client.connect()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Cliente MQTT iniciado correctamente')
            )
            
            self.stdout.write('📡 Esperando mensajes MQTT...')
            self.stdout.write('   (Presiona Ctrl+C para detener)')
            
            # Mantener el cliente corriendo
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en cliente MQTT: {e}')
            )
            logger.error(f'MQTT client error: {e}')
        finally:
            self.stdout.write('🔌 Desconectando cliente MQTT...')
            mqtt_client.disconnect()
            self.stdout.write(
                self.style.SUCCESS('✅ Cliente MQTT desconectado correctamente')
            )