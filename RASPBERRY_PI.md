# 🍓 Home Control Advanced - Instalación en Raspberry Pi

## 📋 Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sensores      │    │  Raspberry Pi   │    │   Actuadores    │
│   (ESP8266)     │    │                 │    │   (ESP8266)     │
│                 │    │  ┌───────────┐  │    │                 │
│  DHT22 ─────────┼────┤  │ Mosquitto │  ├────┼───── Relé       │
│  Temperatura    │    │  │   MQTT    │  │    │  Calefacción    │
│  Humedad        │    │  └───────────┘  │    │                 │
└─────────────────┘    │        │        │    └─────────────────┘
                       │        ▼        │
                       │  ┌───────────┐  │
                       │  │   MQTT    │  │
                       │  │  Bridge   │  │
                       │  └───────────┘  │
                       │        │        │
                       │        ▼        │
                       │  ┌───────────┐  │
                       │  │  Django   │  │    📱 Dashboard Web
                       │  │ + SQLite  ├──┼────► http://rpi:8000
                       │  │  Server   │  │
                       │  └───────────┘  │
                       └─────────────────┘
```

## 🎯 Componentes del Sistema

### 🔧 **En la Raspberry Pi**:
- **Django**: Servidor web y API REST
- **SQLite**: Base de datos local
- **Mosquitto**: Broker MQTT
- **MQTT Bridge**: Puente Python que envía datos MQTT a Django
- **Gunicorn**: Servidor WSGI para Django

### 📡 **Sensores (ESP8266/ESP32)**:
- Lee temperatura y humedad (DHT22)
- Envía datos via MQTT cada 30 segundos
- Envía estado del dispositivo cada 5 minutos

### ⚡ **Actuadores (ESP8266/ESP32)**:
- Controla relé de calefacción
- Recibe comandos via MQTT
- Envía confirmaciones de estado

## 🚀 Instalación Completa

### 1️⃣ **Preparar Raspberry Pi**

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Clonar repositorio (o copiar archivos)
git clone <tu-repositorio> /home/pi/home_control
cd /home/pi/home_control
```

### 2️⃣ **Ejecutar instalación automática**

```bash
# Hacer ejecutables los scripts
chmod +x install_rpi.sh
chmod +x install_services.sh

# Instalar dependencias del sistema
sudo ./install_rpi.sh
```

### 3️⃣ **Configurar proyecto Django**

```bash
# Cambiar al usuario pi
sudo -u pi bash
cd /home/pi/home_control

# Activar entorno virtual
source venv/bin/activate

# Copiar código Django
cp -r backend/ .

# Configurar base de datos
cd backend
python manage.py migrate
python manage.py createsuperuser

# Recopilar archivos estáticos
python manage.py collectstatic --noinput
```

### 4️⃣ **Configurar servicios**

```bash
# Copiar MQTT bridge
cp mqtt_bridge.py /home/pi/home_control/

# Instalar servicios systemd
sudo ./install_services.sh
```

### 5️⃣ **Iniciar sistema**

```bash
# Iniciar servicios
sudo systemctl start home-control-django
sudo systemctl start home-control-mqtt-bridge

# Verificar estado
sudo systemctl status home-control-django
sudo systemctl status home-control-mqtt-bridge
```

## 🔧 Configuración

### **Variables de entorno** (`.env`):
```bash
# Django
DJANGO_SETTINGS_MODULE=home_control.settings.raspberry_pi
DEBUG=False
SECRET_KEY=tu-clave-muy-segura-y-larga
ALLOWED_HOSTS=localhost,127.0.0.1,raspberrypi.local,192.168.1.*

# MQTT
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# API
DJANGO_API_KEY=tu-api-key-segura
DJANGO_URL=http://localhost:8000
```

### **Topics MQTT**:
```
home/sensors/SENSOR_ID/data      → Datos de sensores
home/sensors/SENSOR_ID/status    → Estado de sensores
home/heating/control             → Comandos de calefacción
home/heating/status              → Estado de calefacción
```

## 📡 Configuración de Sensores

### **Hardware necesario**:
- ESP8266 o ESP32
- Sensor DHT22 (temperatura/humedad)
- Resistencia 10kΩ (pull-up)
- Cables de conexión

### **Conexiones**:
```
DHT22     ESP8266
-----     -------
VCC   →   3.3V
GND   →   GND
DATA  →   D2 (GPIO2) + resistencia 10kΩ a 3.3V
```

### **Programación**:
1. Instalar Arduino IDE
2. Agregar board ESP8266/ESP32
3. Instalar librerías:
   - DHT sensor library
   - PubSubClient
   - ArduinoJson
4. Cargar código `sensors_code/sensor_mqtt.ino`
5. Configurar WiFi y IP de Raspberry Pi

## ⚡ Configuración de Actuadores

### **Hardware necesario**:
- ESP8266 o ESP32
- Módulo relé 5V/10A
- Fuente de alimentación para relé
- Optoacoplador (recomendado)

### **Conexiones**:
```
Relé      ESP8266
----      -------
VCC   →   5V (fuente externa)
GND   →   GND común
IN    →   D2 (GPIO2)
```

### **Programación**:
1. Cargar código `sensors_code/actuator_mqtt.ino`
2. Configurar WiFi y IP de Raspberry Pi
3. Configurar pin del relé

## 🔍 Monitoreo y Debugging

### **Ver logs en tiempo real**:
```bash
# Logs de Django
sudo journalctl -u home-control-django -f

# Logs de MQTT Bridge
sudo journalctl -u home-control-mqtt-bridge -f

# Logs de archivos
tail -f /var/log/home_control/*.log
```

### **Verificar MQTT**:
```bash
# Suscribirse a todos los mensajes
mosquitto_sub -h localhost -t "#"

# Enviar mensaje de prueba
mosquitto_pub -h localhost -t "test" -m "Hello World"

# Verificar datos de sensores
mosquitto_sub -h localhost -t "home/sensors/+/data"
```

### **Verificar Django**:
```bash
# Health check
curl http://localhost:8000/health/

# API de sensores
curl http://localhost:8000/sensors/api/readings/

# Dashboard
curl http://localhost:8000/
```

## 🔧 Comandos Útiles

### **Gestión de servicios**:
```bash
# Reiniciar servicios
sudo systemctl restart home-control-django
sudo systemctl restart home-control-mqtt-bridge

# Parar servicios
sudo systemctl stop home-control-django
sudo systemctl stop home-control-mqtt-bridge

# Deshabilitar auto-arranque
sudo systemctl disable home-control-django
sudo systemctl disable home-control-mqtt-bridge
```

### **Gestión de base de datos**:
```bash
cd /home/pi/home_control/backend
source ../venv/bin/activate

# Backup
python manage.py dumpdata > backup.json

# Restore
python manage.py loaddata backup.json

# Shell de Django
python manage.py shell
```

### **Actualización del sistema**:
```bash
# Actualizar código
cd /home/pi/home_control
git pull  # o copiar archivos nuevos

# Reiniciar servicios
sudo systemctl restart home-control-django
sudo systemctl restart home-control-mqtt-bridge
```

## 🌐 Acceso desde otros dispositivos

### **Configurar acceso desde la red local**:

1. **Encontrar IP de Raspberry Pi**:
   ```bash
   hostname -I
   ```

2. **Actualizar ALLOWED_HOSTS** en `.env`:
   ```bash
   ALLOWED_HOSTS=localhost,127.0.0.1,raspberrypi.local,192.168.1.100
   ```

3. **Reiniciar Django**:
   ```bash
   sudo systemctl restart home-control-django
   ```

4. **Acceder desde cualquier dispositivo**:
   - Dashboard: `http://192.168.1.100:8000/`
   - Admin: `http://192.168.1.100:8000/admin/`

## 🔒 Seguridad

### **Configuración básica de seguridad**:

1. **Cambiar contraseñas por defecto**
2. **Configurar firewall**:
   ```bash
   sudo ufw enable
   sudo ufw allow 22    # SSH
   sudo ufw allow 8000  # Django
   sudo ufw allow 1883  # MQTT
   ```

3. **Habilitar autenticación MQTT** (opcional):
   ```bash
   sudo mosquitto_passwd -c /etc/mosquitto/passwd username
   ```

4. **Configurar backup automático**:
   ```bash
   # Agregar a crontab
   0 2 * * * cd /home/pi/home_control/backend && ../venv/bin/python manage.py dumpdata > /home/pi/backup_$(date +\%Y\%m\%d).json
   ```

## 🚨 Troubleshooting

### **Problemas comunes**:

1. **Django no arranca**:
   ```bash
   # Verificar logs
   sudo journalctl -u home-control-django -n 50
   
   # Verificar configuración
   cd /home/pi/home_control/backend
   source ../venv/bin/activate
   python manage.py check
   ```

2. **MQTT Bridge no conecta**:
   ```bash
   # Verificar Mosquitto
   sudo systemctl status mosquitto
   
   # Probar conexión manual
   mosquitto_pub -h localhost -t test -m "test"
   ```

3. **Sensores no envían datos**:
   - Verificar conexión WiFi del ESP
   - Verificar IP de Raspberry Pi en código
   - Verificar logs de MQTT: `mosquitto_sub -h localhost -t "#"`

4. **Actuadores no responden**:
   - Verificar suscripción MQTT en el ESP
   - Verificar topic: `home/heating/control`
   - Enviar comando manual: `mosquitto_pub -h localhost -t "home/heating/control" -m '{"action":"turn_on"}'`

## 📊 Optimización para Raspberry Pi

### **Configuración para SD card**:
- Logs rotativos configurados
- SQLite optimizado
- Caché en memoria
- Escrituras mínimas

### **Rendimiento**:
- 2 workers Gunicorn (ajustar según RAM)
- Timeout de 60 segundos
- Compresión de archivos estáticos

### **Monitoreo de recursos**:
```bash
# CPU y memoria
htop

# Espacio en disco
df -h

# Temperatura de CPU
vcgencmd measure_temp
```

¡Tu sistema de control de calefacción está listo para funcionar en Raspberry Pi! 🎉