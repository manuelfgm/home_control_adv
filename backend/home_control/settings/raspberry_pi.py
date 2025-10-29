"""
Configuración para Raspberry Pi (local)
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Hosts permitidos (incluir IP de la Raspberry Pi)
ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1', 
    '0.0.0.0',
    '192.168.1.*',  # Rango típico de red local
    os.getenv('RPI_IP', 'raspberrypi.local'),
]

# Database para Raspberry Pi - usar SQLite para simplicidad
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 60,  # Timeout más largo para SD card
        }
    }
}

# Static files para Raspberry Pi
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# WhiteNoise para servir archivos estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# CORS settings para acceso local
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://raspberrypi.local:8000",
]

# CSRF settings para Raspberry Pi
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000', 
    'http://raspberrypi.local:8000',
]

# Cache simple en memoria
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'rpi-home-control-cache',
        'TIMEOUT': 300,
    }
}

# Session storage en base de datos
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Email backend para desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# MQTT Configuration para Raspberry Pi
MQTT_BROKER = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', 60))
MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'rpi_home_control')

# Configuración optimizada para Raspberry Pi
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB (más pequeño para RPi)
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Logging optimizado para SD card
# Asegurar que el directorio existe
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING['handlers']['file']['filename'] = LOGS_DIR / 'django.log'
LOGGING['root']['level'] = 'WARNING'  # Menos logs para preservar SD card

# REST Framework optimizado
REST_FRAMEWORK['PAGE_SIZE'] = 25  # Páginas más pequeñas

# Security settings básicas
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Permitir frames de mismo origen

# Configuración específica para MQTT bridge
MQTT_BRIDGE_ENABLED = True
MQTT_BRIDGE_TOPICS = {
    'sensor_data': 'home/sensors/+/data',      # home/sensors/room1/data
    'heating_control': 'home/heating/control',  # home/heating/control
    'heating_status': 'home/heating/status',    # home/heating/status
}