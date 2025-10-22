# 🛠️ Comandos Útiles del Sistema

## 🚀 Comandos de Django

### Gestión de Base de Datos
```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Shell interactivo
python manage.py shell
```

### Comandos Personalizados del Proyecto

#### 📡 Cliente MQTT
```bash
# Iniciar cliente MQTT (modo interactivo)
python manage.py start_mqtt

# Iniciar cliente MQTT en segundo plano
nohup python manage.py start_mqtt > logs/mqtt.log 2>&1 &

# Verificar si está corriendo
pgrep -f "start_mqtt"

# Matar proceso MQTT
pkill -f "start_mqtt"
```

#### 🔥 Control de Calefacción
```bash
# Evaluar horarios manualmente
python manage.py evaluate_heating

# Evaluar con información detallada
python manage.py evaluate_heating --verbose

# Evaluar controlador específico
python manage.py evaluate_heating --controller-id=main_heating
```

#### 🧹 Limpieza de Datos
```bash
# Ver qué se eliminaría (sin eliminar)
python manage.py cleanup_old_data --dry-run

# Limpiar datos de más de 365 días
python manage.py cleanup_old_data

# Limpiar datos de más de 30 días
python manage.py cleanup_old_data --days=30

# Limpiar con información detallada
python manage.py cleanup_old_data --days=90 --verbosity=2
```

## ⏰ Gestión de Cronjobs

### Configurar Cronjobs
```bash
# Instalar cronjobs automáticamente
./setup_cron.sh

# Ver cronjobs actuales
crontab -l

# Editar cronjobs manualmente
crontab -e

# Eliminar todos los cronjobs
crontab -r
```

### Cronjobs Configurados
```bash
# Evaluar calefacción cada minuto
* * * * * cd /ruta/proyecto/backend && python manage.py evaluate_heating

# Limpiar datos diariamente a las 2:00 AM
0 2 * * * cd /ruta/proyecto/backend && python manage.py cleanup_old_data

# Verificar sensores cada 5 minutos
*/5 * * * * cd /ruta/proyecto/backend && python manage.py shell -c "..."

# Mantener MQTT corriendo cada 2 minutos
*/2 * * * * pgrep -f 'start_mqtt' > /dev/null || (cd /ruta && nohup python manage.py start_mqtt &)
```

## 📊 Monitoreo y Logs

### Ver Logs en Tiempo Real
```bash
# Logs de Django
tail -f logs/django.log

# Logs de MQTT
tail -f logs/mqtt_cron.log

# Logs de evaluación de calefacción
tail -f logs/heating_cron.log

# Logs de limpieza de datos
tail -f logs/cleanup_cron.log

# Todos los logs de cronjobs
tail -f logs/*.log
```

### Verificar Estado del Sistema
```bash
# Estado de procesos
ps aux | grep -E "(django|start_mqtt)"

# Uso de memoria y CPU
top -p $(pgrep -d',' -f "python.*manage.py")

# Espacio en disco de la base de datos
ls -lh backend/db.sqlite3

# Verificar conectividad MQTT (requiere mosquitto-clients)
mosquitto_pub -h io.adafruit.com -u tu_usuario -P tu_password -t test/topic -m "test"
```

## 🔧 Comandos de Desarrollo

### Debugging
```bash
# Ejecutar con debug activado
DEBUG=True python manage.py runserver

# Shell con imports automáticos
python manage.py shell_plus

# Mostrar URLs disponibles
python manage.py show_urls

# Revisar configuración
python manage.py diffsettings
```

### Testing
```bash
# Ejecutar todos los tests
python manage.py test

# Test específico
python manage.py test sensors.tests

# Test con coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Base de Datos
```bash
# Dump de datos
python manage.py dumpdata > backup.json

# Cargar datos
python manage.py loaddata backup.json

# Dump de horarios específicamente
python manage.py dumpdata heating.HeatingSchedule > schedules_backup.json

# SQL directo
python manage.py dbshell
```

## 🐛 Solución de Problemas

### MQTT no conecta
```bash
# Verificar configuración
python manage.py shell -c "from django.conf import settings; print(f'MQTT: {settings.MQTT_USERNAME}@{settings.MQTT_BROKER}')"

# Test de conectividad manual
python -c "
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.username_pw_set('tu_usuario', 'tu_password')
client.connect('io.adafruit.com', 1883, 60)
print('Conexión exitosa')
"
```

### Calefacción no responde
```bash
# Verificar estado actual
python manage.py shell -c "
from heating.models import HeatingControl
control = HeatingControl.objects.get(controller_id='main_heating')
print(f'Estado: {control.status}, Calentando: {control.is_heating}')
print(f'Temp actual: {control.current_temperature}, Objetivo: {control.target_temperature}')
"

# Forzar evaluación
python manage.py evaluate_heating --verbose

# Enviar comando manual via API
curl -X POST http://localhost:8000/heating/api/control/1/manual_override/ \
  -H "Content-Type: application/json" \
  -d '{"turn_on": true, "duration_hours": 1}'
```

### Limpiar todo y empezar de nuevo
```bash
# Parar todos los procesos
pkill -f "start_mqtt"
pkill -f "runserver"

# Eliminar base de datos
rm backend/db.sqlite3

# Recrear base de datos
python manage.py migrate

# Recrear superusuario
python manage.py createsuperuser

# Reconfigurar cronjobs
./setup_cron.sh
```

## 📈 Comandos de Producción

### Recopilar archivos estáticos
```bash
python manage.py collectstatic
```

### Usar Gunicorn en producción
```bash
# Instalar Gunicorn
pip install gunicorn

# Ejecutar con Gunicorn
gunicorn home_control.wsgi:application --bind 0.0.0.0:8000

# Con configuración específica
gunicorn home_control.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 30 \
  --max-requests 1000
```