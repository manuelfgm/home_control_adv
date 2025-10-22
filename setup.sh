#!/bin/bash

# Script de configuración inicial para el proyecto de control de calefacción

echo "🏠 Configurando proyecto de Control de Calefacción..."

# Crear archivos de configuración si no existen
if [ ! -f "backend/.env" ]; then
    echo "📋 Creando archivo de configuración backend/.env..."
    cp backend/.env.example backend/.env
    echo "⚠️  IMPORTANTE: Edita backend/.env con tus datos de Adafruit IO"
fi

if [ ! -f "controller/config.h" ]; then
    echo "📋 Creando archivo de configuración controller/config.h..."
    cp controller/config.h.example controller/config.h
    echo "⚠️  IMPORTANTE: Edita controller/config.h con tus datos de WiFi y Adafruit IO"
fi

echo "🐍 Configurando entorno Python..."
cd backend

# Activar entorno virtual si existe
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
    echo "✅ Entorno virtual activado"
else
    echo "❌ No se encontró entorno virtual. Ejecútalo primero desde VS Code."
    exit 1
fi

# Ejecutar migraciones
echo "🗃️  Ejecutando migraciones de base de datos..."
python manage.py makemigrations
python manage.py migrate

# Crear superusuario si no existe
echo "👤 Creando superusuario para Django Admin..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@localhost', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

# Crear datos iniciales
echo "📊 Creando datos iniciales..."
python manage.py shell << EOF
from heating.models import HeatingControl, TemperatureThreshold
from sensors.models import SensorStatus

# Crear control de calefacción principal
control, created = HeatingControl.objects.get_or_create(
    controller_id='main_heating',
    defaults={
        'name': 'Calefacción Principal',
        'status': 'auto'
    }
)
if created:
    print("✅ Control de calefacción creado")

# Crear umbral de temperatura por defecto
threshold, created = TemperatureThreshold.objects.get_or_create(
    name='Default',
    defaults={
        'high_temperature': 22.0,
        'low_temperature': 18.0,
        'hysteresis': 0.5
    }
)
if created:
    print("✅ Umbral de temperatura creado")

# Crear sensor por defecto
sensor, created = SensorStatus.objects.get_or_create(
    sensor_id='room_sensor',
    defaults={
        'name': 'Sensor de Habitación',
        'location': 'Salón',
        'is_active': True
    }
)
if created:
    print("✅ Sensor por defecto creado")

print("🎉 Datos iniciales configurados correctamente")
EOF

echo ""
echo "🎉 ¡Configuración completada!"
echo ""
echo "📝 Próximos pasos:"
echo "1. Edita backend/.env con tus credenciales de Adafruit IO"
echo "2. Edita controller/config.h con tus datos de WiFi y Adafruit IO"
echo "3. Sube el código del sensor (room/room.ino) a tu ESP8266 sensor"
echo "4. Sube el código del controlador (controller/heating_controller.ino) a tu ESP8266 controlador"
echo "5. Conecta el relé al pin D1 del ESP8266 controlador"
echo "6. Inicia el servidor Django: python manage.py runserver"
echo "7. Visita http://localhost:8000 para acceder al dashboard"
echo ""
echo "🔧 Para acceder al admin de Django:"
echo "   Usuario: admin"
echo "   Contraseña: admin123"
echo "   URL: http://localhost:8000/admin/"
echo ""
echo "📖 Consulta el README.md para más información"