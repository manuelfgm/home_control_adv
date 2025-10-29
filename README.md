# 🏠 Home Control Advanced - Sistema de Control de Calefacción

Sistema completo de control domótico para calefacción con sensores IoT, dashboard web y automatización inteligente.

## ✨ Características Principales

### 🌡️ **Sistema de Perfiles de Temperatura**
- **Temperatura Mínima Configurable** - Protección anti-congelación automática
- **Perfiles Múltiples** - Normal, Vacaciones, Económico, Nocturno, Personalizado  
- **Modo Día/Noche Automático** - Temperaturas diferentes según horario
- **Activación con Un Clic** - Modo vacaciones instantáneo

### 📅 **Programación Avanzada**
- **Horarios Multi-día** - Programación semanal completa
- **Prevención de Conflictos** - Validación automática de solapamientos
- **Compatibilidad Total** - Los perfiles respetan horarios programados

### 🌐 **Dashboard Web Moderno**
- **SPA (Single Page Application)** - Sin recargas de página
- **JavaScript Puro** - Interfaz responsiva y rápida
- **API REST Completa** - Endpoints para todas las funciones
- **Control en Tiempo Real** - Monitoreo y control instantáneo

### 🔌 **IoT & Comunicaciones**
- **Sensores ESP8266/ESP32** - Temperatura y humedad DHT22
- **Actuadores Remotos** - Control de relés via MQTT
- **Configuración Segura** - Credenciales separadas en archivos config.h
- **Bridge MQTT-Django** - Integración automática de datos

## 🏗️ Arquitectura del Sistema

```
📡 Sensores ESP ──MQTT──► 🍓 Raspberry Pi ──MQTT──► ⚡ Actuadores ESP
                           │
                           ├─ Mosquitto MQTT Broker
                           ├─ MQTT Bridge (Python)  
                           ├─ Django API + SQLite
                           ├─ Dashboard Web :8000
                           └─ Perfiles de Temperatura
```

## 🚀 Instalación Rápida (Raspberry Pi)

```bash
# 1. Clonar repositorio
git clone <tu-repo> /home/pi/home_control
cd /home/pi/home_control

# 2. Ejecutar instalación automática
sudo ./install_rpi.sh

# 3. Configurar Django
sudo -u pi bash
cd /home/pi/home_control
source venv/bin/activate
cd backend
python manage.py migrate
python manage.py createsuperuser

# 4. Instalar servicios systemd
sudo ./install_services.sh

# 5. Probar sistema
python test_system.py
```

## 🌐 Acceso al Sistema

- **Dashboard**: http://raspberry-pi-ip:8000/
- **Admin**: http://raspberry-pi-ip:8000/admin/
- **API**: http://raspberry-pi-ip:8000/api/

### 📊 **Páginas del Dashboard**
- **Inicio** (`/`) - Vista general y estado actual
- **Horarios** (`/schedules/`) - Programación semanal
- **Perfiles** (`/profiles/`) - Gestión de perfiles de temperatura
- **Histórico** (`/history/`) - Gráficos y estadísticas
- **Control** (`/control/`) - Control manual

## 🔧 Configuración ESP32/ESP8266

### 📁 **Estructura de Archivos**
```
esp/
├── sensor_mqtt/
│   ├── sensor_mqtt.ino      # Código principal
│   ├── config.h.example     # Plantilla configuración
│   └── config.h             # Tu configuración (no en git)
└── actuator_mqtt/
    ├── actuator_mqtt.ino    # Código principal
    ├── config.h.example     # Plantilla configuración
    └── config.h             # Tu configuración (no en git)
```

### ⚙️ **Configuración Inicial**
```bash
# 1. Copiar archivos de configuración
cd esp/sensor_mqtt/
cp config.h.example config.h

cd ../actuator_mqtt/
cp config.h.example config.h

# 2. Editar con tus credenciales
nano sensor_mqtt/config.h
nano actuator_mqtt/config.h
```

### 🔌 **Hardware Necesario**

#### **Sensor (DHT22)**
- ESP32/ESP8266
- Sensor DHT22
- Resistencia 10kΩ (pull-up)
- Cables de conexión

#### **Actuador (Relé)**
- ESP32/ESP8266  
- Módulo relé (5V/3.3V)
- LED indicador (opcional)
- Fuente de alimentación

## 📡 API Endpoints

### 🌡️ **Perfiles de Temperatura**
```bash
GET    /heating/api/profiles/                 # Listar perfiles
POST   /heating/api/profiles/                 # Crear perfil
PUT    /heating/api/profiles/{id}/            # Actualizar perfil
DELETE /heating/api/profiles/{id}/            # Eliminar perfil

# Endpoints especiales
GET    /heating/api/profiles/active_profile/  # Perfil activo
GET    /heating/api/profiles/current_status/  # Estado actual
POST   /heating/api/profiles/activate_profile/ # Activar perfil
GET    /heating/api/profiles/vacation_mode/   # Modo vacaciones
```

### 📅 **Horarios y Control**
```bash
GET    /heating/api/schedules/               # Horarios programados
GET    /heating/api/control/                 # Estado del sistema
POST   /heating/api/control/manual_override/ # Control manual
GET    /heating/api/logs/                    # Historial de eventos
```

### 📊 **Sensores**
```bash
GET    /sensors/api/readings/                # Lecturas de sensores
GET    /sensors/api/status/                  # Estado de sensores
```

## 🏠 Casos de Uso

### 🏡 **Uso Diario Normal**
1. Perfil "Normal" activo por defecto
2. Temperatura confort: 20°C (día)
3. Temperatura nocturna: 17°C (23:00-06:00)
4. Protección mínima: 16°C (siempre)

### ✈️ **Modo Vacaciones**
1. Un clic en "Activar Modo Vacaciones"
2. Temperaturas reducidas para ahorro
3. Protección básica: 12°C
4. Regreso fácil al modo normal

### 💰 **Ahorro Energético**
1. Perfil "Económico" con temperaturas reducidas
2. Activación automática configurable
3. Balance entre confort y eficiencia

### 🛡️ **Protección Anti-Congelación**
1. Temperatura mínima SIEMPRE respetada
2. Independiente de horarios programados
3. Protección automática de tuberías

## 📂 Estructura del Proyecto

```
home_control_adv/
├── 📄 README.md
├── 📄 RASPBERRY_PI.md          # Guía detallada RPi
├── 📄 TEMPERATURE_PROFILES.md  # Documentación perfiles
├── 📦 requirements.txt
├── 🚀 install_rpi.sh           # Instalación automática
├── ⚙️ install_services.sh      # Servicios systemd
├── 🌉 mqtt_bridge.py           # Bridge MQTT-Django
├── 🧪 test_system.py           # Tests del sistema
├── 📁 backend/                 # Django + API REST
│   ├── 🏠 dashboard/           # SPA Dashboard
│   ├── 🌡️ heating/            # Control calefacción
│   ├── 📊 sensors/             # Gestión sensores
│   └── ⚙️ home_control/        # Configuración Django
└── 📁 esp/                     # Código Arduino
    ├── 📊 sensor_mqtt/         # ESP sensor DHT22
    └── ⚡ actuator_mqtt/       # ESP actuador relé
```

## 🔐 Seguridad

- **Archivos config.h** están en `.gitignore`
- **Credenciales WiFi/MQTT** separadas del código
- **Autenticación Django** en dashboard web
- **Protección CSRF** en todas las APIs

## 🆘 Solución de Problemas

### ❌ **Error: No module named 'django'**
```bash
# Activar entorno virtual
source venv/bin/activate
```

### ❌ **Error: logs/django.log no encontrado**
```bash
# Crear directorio de logs
mkdir -p backend/logs
```

### ❌ **Sensores no conectan a MQTT**
1. Verificar credenciales WiFi en `config.h`
2. Comprobar IP del Raspberry Pi
3. Verificar que Mosquitto esté funcionando

### ❌ **Dashboard no carga datos**
1. Verificar que Django esté ejecutándose
2. Comprobar que MQTT bridge esté activo
3. Revisar logs: `journalctl -u home-control-django`

## 📝 Logs y Monitoreo

```bash
# Logs del sistema
journalctl -u home-control-django -f
journalctl -u home-control-mqtt-bridge -f

# Logs de Django
tail -f /home/pi/home_control/backend/logs/django.log

# Estado de servicios
systemctl status home-control-django
systemctl status home-control-mqtt-bridge
systemctl status mosquitto
```

## 🤝 Contribuir

1. Fork del repositorio
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

---

**🏠 Home Control Advanced** - Control inteligente de calefacción para el hogar moderno