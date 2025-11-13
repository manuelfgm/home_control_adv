# 🏠 Home Control Advanced

Sistema completo de control de calefacción domótica con Django, MQTT y ESP32/ESP8266.

## 📋 Características

- 🌡️ **Control automático de calefacción** con horarios configurables
- 📊 **API REST completa** para sensores y actuadores
- 🔌 **Bridge MQTT** para comunicación con dispositivos ESP
- 📱 **Panel de administración Django** para configuración
- ⚙️ **Servicio systemd** para ejecución 24/7
- 📈 **Logs y monitorización** integrados

## 🚀 Instalación Rápida

### 1. Preparar el Sistema
```bash
# Instalar dependencias
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git

# Clonar o copiar el proyecto
cd /home/manu/personalcode/
# (aquí debes tener la carpeta home_control_adv)
```

### 2. Configurar el Proyecto
```bash
cd /home/manu/personalcode/home_control_adv

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
cd backend
python manage.py migrate
python manage.py createsuperuser  # Crear usuario admin
```

### 3. Instalar Servicio de Producción
```bash
# Instalar servicio systemd
./manage_service.sh install
```

## 🎯 Comandos de Producción

### **Gestión Principal del Servicio**
```bash
# Iniciar el servicio
sudo systemctl start home-control-backend

# Reiniciar el servicio (soluciona conflictos de puerto)
sudo systemctl restart home-control-backend

# Detener el servicio
sudo systemctl stop home-control-backend

# Ver estado detallado
sudo systemctl status home-control-backend

# Habilitar inicio automático al arrancar
sudo systemctl enable home-control-backend

# Deshabilitar inicio automático
sudo systemctl disable home-control-backend
```

### **Monitorización y Logs**
```bash
# Ver logs en tiempo real
journalctl -u home-control-backend -f

# Ver últimos logs
journalctl -u home-control-backend -n 50

# Ver logs de hoy
journalctl -u home-control-backend --since today

# Ver logs con filtros
journalctl -u home-control-backend --since "1 hour ago"
```


### **Gestión de Configuración**
```bash
# Recargar configuración de systemd (después de cambios)
sudo systemctl daemon-reload

# Ver configuración del servicio
systemctl show home-control-backend

# Ver archivos de configuración activos
systemctl cat home-control-backend
```

## 🔧 Comandos de Desarrollo

### **Para Testing y Desarrollo**
```bash
# Servidor de desarrollo (puerto 8001)
./start_dev.sh

# Consola interactiva Django
cd backend && python manage.py shell

# Ejecutar migraciones
cd backend && python manage.py migrate

# Crear superusuario
cd backend && python manage.py createsuperuser

# Recolectar archivos estáticos
cd backend && python manage.py collectstatic
```

## 🌐 Acceso al Sistema

### **URLs Principales**
- **Panel Admin**: http://localhost:8000/admin/
- **API Sensors**: http://localhost:8000/sensors/api/readings/
- **API Actuators**: http://localhost:8000/actuators/api/status/
- **API Heating**: http://localhost:8000/heating/api/settings/current/

## 📡 Configuración MQTT

### **Topics MQTT**
```bash
# Sensores envían datos a:
home/sensors/SENSOR_ID/data

# Actuadores reciben comandos en:
home/actuator/ACTUATOR_ID/command

# Actuadores envían estado a:
home/actuator/ACTUATOR_ID/data
```

### **Formato de Mensajes**

**Sensor (entrada):**
```json
{
  "sensor_id": "living_room",
  "temperature": 22.5,
  "humidity": 65.0,
  "wifi_signal": -45,
  "free_heap": 25000,
  "sensor_error": false
}
```

**Comando a Actuador (salida):**
```json
{
  "temperature": 20.5,
  "action": "turn_on",
  "timestamp": "2025-11-13T10:30:00Z"
}
```

## 🛠️ Resolución de Problemas

### **Problemas Comunes**

**1. Servicio no inicia:**
```bash
# Ver logs detallados
journalctl -u home-control-backend -n 100

# Verificar configuración
sudo systemctl status home-control-backend

# Reiniciar completamente
sudo systemctl restart home-control-backend
```

**2. Puerto 8000 ocupado:**
```bash
# Ver qué proceso usa el puerto
sudo netstat -tlnp | grep :8000

# Reiniciar servicio (mata procesos automáticamente)
sudo systemctl restart home-control-backend
```

**3. MQTT no conecta:**
```bash
# Verificar broker MQTT
sudo systemctl status mosquitto

# Ver configuración MQTT en .env
cat .env | grep MQTT

# Ver logs específicos de MQTT
journalctl -u home-control-backend | grep MQTT
```

**4. Base de datos corrupta:**
```bash
# Backup de seguridad
cp backend/db.sqlite3 backup_$(date +%Y%m%d).sqlite3

# Recrear migraciones si es necesario
cd backend
python manage.py migrate --fake-initial
```

### **Comandos de Diagnóstico**
```bash
# Verificar todos los servicios
./check_status.sh

# Ver procesos relacionados
ps aux | grep -E "(gunicorn|mqtt_bridge|home_control)"

# Ver puertos abiertos
sudo netstat -tlnp | grep -E "(8000|1883)"

# Test de conectividad API
curl -s http://localhost:8000/heating/api/settings/current/ | jq

# Ver uso de recursos
top -p $(pgrep -f home_control)
```

## 📁 Estructura del Proyecto

```
home_control_adv/
├── backend/                    # Django backend
│   ├── home_control/          # Configuración principal
│   ├── sensors/               # App de sensores
│   ├── actuators/             # App de actuadores
│   ├── heating/               # App de calefacción
│   └── db.sqlite3             # Base de datos
├── mqtt_bridge.py             # Bridge MQTT-Django
├── requirements.txt           # Dependencias Python
├── .env                       # Variables de entorno
├── gunicorn.conf.py          # Configuración Gunicorn
├── start_backend.sh          # Script complejo (no usar en producción)
├── start_dev.sh              # Script de desarrollo
├── manage_service.sh         # Gestión servicio systemd
├── home-control-backend.service  # Definición servicio
├── quick_check.sh            # Verificación rápida
├── check_status.sh           # Verificación completa
├── dashboard.sh              # Dashboard visual
└── test_system.sh            # Test funcional
```

## 🔒 Seguridad en Producción

### **Configuración Recomendada**
```bash
# Cambiar DEBUG a False en .env
echo "DEBUG=False" >> .env

# Generar SECRET_KEY segura
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))" >> .env

# Configurar ALLOWED_HOSTS
echo "ALLOWED_HOSTS=localhost,127.0.0.1,tu-ip-raspberry" >> .env

# Reiniciar después de cambios
sudo systemctl restart home-control-backend
```

### **Backup Automático**
```bash
# Agregar backup diario al crontab
crontab -e

# Agregar línea:
0 2 * * * cd /home/manu/personalcode/home_control_adv && cp backend/db.sqlite3 "backups/db_backup_$(date +\%Y\%m\%d).sqlite3"
```

## 📞 Soporte

### **Comandos de Ayuda**
```bash
./manage_service.sh          # Ver opciones del servicio
./quick_check.sh             # Estado rápido
./check_status.sh            # Diagnóstico completo
systemctl --help             # Ayuda de systemctl
journalctl --help            # Ayuda de logs
```

### **Información del Sistema**
- **Framework**: Django 5.2.8 + Django REST Framework
- **Servidor**: Gunicorn + WhiteNoise  
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **MQTT**: paho-mqtt 2.1.0
- **Plataforma**: Linux systemd

---

🎉 **¡Tu sistema de control doméstico está listo para funcionar 24/7!**
