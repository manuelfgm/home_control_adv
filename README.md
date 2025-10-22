# 🏠 Sistema de Control de Calefacción Avanzado

Sistema completo de domótica para controlar la calefacción del hogar mediante sensores de temperatura, MQTT (Adafruit IO) y una interfaz web desarrollada en Django.

## 🌟 Características

- **🌡️ Monitoreo de temperatura y humedad** en tiempo real
- **⏰ Programación de horarios** personalizables por día de la semana
- **🔥 Control automático y manual** de la calefacción
- **📊 Dashboard web intuitivo** con gráficos históricos
- **📡 Comunicación MQTT** via Adafruit IO
- **📱 Interfaz responsive** para acceso desde móviles
- **⚡ Sistema en tiempo real** con actualizaciones automáticas
- **📈 Estadísticas y análisis** de uso energético

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    MQTT     ┌─────────────────┐    WiFi    ┌─────────────────┐
│   Sensor DHT22  │──Adafruit──▶│ Scripts Python  │◀──────────│ Controlador ESP │
│   (ESP8266)     │     IO      │ (Independientes)│           │   + Relé        │
└─────────────────┘             └─────────────────┘           └─────────────────┘
                                          │                            │
                                          │ SQLite                     │ Control
                                          ▼                            ▼
                                ┌─────────────────┐           ┌─────────────────┐
                                │ Django Backend  │           │   Calefacción   │
                                │  (Dashboard)    │           │   del Hogar     │
                                └─────────────────┘           └─────────────────┘
```

### 🔄 **Flujo de Datos:**
1. **Sensores ESP8266** → Envían datos via MQTT → **Scripts independientes**
2. **Scripts independientes** → Procesan datos → **Base de datos SQLite**
3. **Django** → Lee datos de SQLite → **Dashboard web**
4. **Scripts independientes** → Evalúan horarios → **Envían comandos MQTT**
5. **Controlador ESP8266** → Recibe comandos → **Controla relé de calefacción**

## 📦 Componentes del Proyecto

### Scripts Independientes (Python)
- **scripts/mqtt_client.py**: Cliente MQTT independiente para recibir datos de sensores
- **scripts/heating_evaluator.py**: Evaluador de horarios y control de calefacción
- **scripts/cleanup.py**: Limpiador de datos antiguos para optimizar la BD
- **scripts/sensor_check.py**: Verificador de estado de sensores

### Backend (Django)
- **sensors/**: Modelos y API para gestión de sensores y lecturas
- **heating/**: Modelos y API para control de calefacción y horarios
- **dashboard/**: Interfaz web y visualización de datos
- **API REST**: Endpoints para consulta y control remoto

### Hardware
- **room/room.ino**: Código para sensor de temperatura (ESP8266 + DHT22)
- **controller/heating_controller.ino**: Código para controlador de calefacción (ESP8266 + Relé)

### Interfaz Web
- Dashboard en tiempo real con gráficos de temperatura
- Configuración de horarios por día de la semana
- Control manual de calefacción
- Visualización de estadísticas históricas

## 🚀 Instalación y Configuración

### Prerrequisitos

- **Python 3.8+** y entorno virtual
- **Arduino IDE** o PlatformIO
- **Cuenta en Adafruit IO** (gratuita)
- **2 x ESP8266** (NodeMCU o Wemos D1 Mini)
- **Sensor DHT22**
- **Módulo de relé de 5V**
- **Conexiones de calefacción** (según tu instalación)

### 1. Configuración del Backend

```bash
# Clonar el repositorio
git clone https://github.com/manuelfgm/home_control_adv.git
cd home_control_adv

# Ejecutar script de configuración
./setup.sh
```

### 2. Configuración de Adafruit IO

1. Crear cuenta en [Adafruit IO](https://io.adafruit.com)
2. Obtener tu **Username** y **AIO Key**
3. Crear los siguientes feeds:
   - `home.room.status` (para datos del sensor)
   - `home.heating.control` (para comandos al controlador)
   - `home.heating.status` (para estado del controlador)

### 3. Configuración del Sensor

```cpp
// Editar controller/config.h con tus datos
const char* WIFI_ID = "TuWiFi";
const char* WIFI_PSSWD = "TuClave";
const char* MQTT_USERNAME = "tu_usuario_adafruit";
const char* MQTT_PASSWORD = "tu_aio_key";
```

**Conexiones del sensor:**
- DHT22 Data → D3
- DHT22 VCC → 3.3V
- DHT22 GND → GND

### 4. Configuración del Controlador

**Conexiones del controlador:**
- Relé IN → D1
- Relé VCC → 5V (USB)
- Relé GND → GND
- LED de estado → D2 (opcional)

### 5. Configuración del Backend

```bash
# Editar backend/.env con tus credenciales
MQTT_USERNAME=tu_usuario_adafruit
MQTT_PASSWORD=tu_aio_key

# Ejecutar migraciones y crear datos iniciales
cd backend
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar el servidor Django
python manage.py runserver
```

### 6. Configurar Tareas Automáticas (Cronjobs)

```bash
# Configurar cronjobs para tareas en segundo plano
./setup_cron.sh

# O manualmente:
crontab -e
# Agregar estas líneas:
# Evaluar calefacción cada minuto
* * * * * cd /ruta/proyecto/backend && python manage.py evaluate_heating

# Limpiar datos antiguos diariamente
0 2 * * * cd /ruta/proyecto/backend && python manage.py cleanup_old_data

# Mantener MQTT corriendo
*/2 * * * * pgrep -f 'start_mqtt' > /dev/null || (cd /ruta/proyecto/backend && nohup python manage.py start_mqtt &)
```

## 💻 Uso del Sistema

### Iniciar el Sistema

```bash
# 1. Iniciar servidor Django
cd backend
python manage.py runserver

# 2. Iniciar cliente MQTT (en otra terminal)
python manage.py start_mqtt

# 3. Configurar cronjobs (una sola vez)
cd ..
./setup_cron.sh
```

### Dashboard Web (http://localhost:8000)

1. **Vista Principal**: Temperatura actual, estado de calefacción, gráficos históricos
2. **Horarios**: Configurar temperaturas por día y hora
3. **Control Manual**: Encender/apagar calefacción manualmente
4. **Histórico**: Análisis de uso y eficiencia energética

### Configuración de Horarios

```
Ejemplo de configuración:
- Lunes a Viernes: 07:00-09:00 → 22°C (mañana)
- Lunes a Viernes: 18:00-23:00 → 21°C (tarde/noche)
- Sábado/Domingo: 08:00-23:00 → 20°C (todo el día)
```

### API REST

**Endpoints principales:**
- `GET /sensors/api/readings/latest/` - Últimas lecturas
- `GET /heating/api/control/` - Estado de calefacción
- `POST /heating/api/control/1/manual_override/` - Control manual
- `GET /heating/api/schedules/` - Horarios configurados

## 🔧 Funcionalidades Avanzadas

### Control Inteligente
- **Histéresis configurable** para evitar ciclos cortos
- **Predicción de temperatura** basada en tendencias
- **Modo de ahorro energético** fuera de horarios

### Monitoreo y Alertas
- Estado online/offline de sensores
- Alertas por temperatura extrema
- Registro detallado de actividad

### Seguridad
- **Modo seguro**: Apagado automático si no hay comunicación
- **Límites de temperatura** configurables
- **Override temporal** con duración límite

## 📊 Análisis y Estadísticas

El sistema proporciona:
- **Tiempo total de funcionamiento** por período
- **Número de ciclos** de encendido/apagado
- **Eficiencia energética** estimada
- **Patrones de uso** y recomendaciones

## 🛠️ Mantenimiento

### Logs del Sistema
```bash
# Ver logs en tiempo real
tail -f backend/logs/heating.log

# Revisar actividad del controlador
# Los logs aparecen en Serial Monitor del Arduino
```

### Backup de Configuración
```bash
# Exportar configuración
python manage.py dumpdata heating.HeatingSchedule > schedules_backup.json

# Importar configuración
python manage.py loaddata schedules_backup.json
```

## 🔍 Resolución de Problemas

### Sensor no reporta datos
1. Verificar conexión WiFi del ESP8266
2. Comprobar credenciales de Adafruit IO
3. Revisar conexiones del DHT22

### Calefacción no responde
1. Verificar que el controlador está online
2. Comprobar conexiones del relé
3. Revisar configuración MQTT

### Problemas de conectividad
1. Verificar red WiFi estable
2. Comprobar firewall y puertos
3. Reiniciar dispositivos ESP8266

## 📈 Próximas Mejoras

- **Integración con Google Home/Alexa**
- **App móvil nativa**
- **Múltiples zonas de calefacción**
- **Machine Learning para optimización**
- **Integración con APIs de tiempo**

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

**Manuel FGM** - [GitHub](https://github.com/manuelfgm)

## 🙏 Agradecimientos

- [Adafruit IO](https://io.adafruit.com) por la plataforma MQTT gratuita
- [Django](https://djangoproject.com) por el framework web
- [Chart.js](https://chartjs.org) por los gráficos
- [Bootstrap](https://getbootstrap.com) por el diseño responsive

---

**⚠️ Importante**: Este sistema controla instalaciones eléctricas. Asegúrate de que las conexiones sean realizadas por un profesional cualificado y cumplan con las normativas locales de seguridad eléctrica.