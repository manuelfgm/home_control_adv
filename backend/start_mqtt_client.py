import os
import django
import logging
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'home_control.settings')
django.setup()

from sensors.mqtt_client import mqtt_client

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Función principal para iniciar el cliente MQTT"""
    logger.info("Iniciando cliente MQTT para control de calefacción")
    
    try:
        # Conectar al broker MQTT
        mqtt_client.connect()
        
        logger.info("Cliente MQTT iniciado correctamente")
        logger.info("Presiona Ctrl+C para detener")
        
        # Mantener el cliente corriendo
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Deteniendo cliente MQTT...")
        mqtt_client.disconnect()
        logger.info("Cliente MQTT detenido")
    except Exception as e:
        logger.error(f"Error en cliente MQTT: {e}")
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()