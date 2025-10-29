# Configuración ESP32/ESP8266

## Configuración Inicial

### 1. Copiar archivos de configuración

Para cada módulo (sensor_mqtt y actuator_mqtt):

```bash
cd esp/sensor_mqtt/
cp config.h.example config.h

cd ../actuator_mqtt/
cp config.h.example config.h
```

### 2. Editar configuración

Edita cada archivo `config.h` con tus datos:

#### WiFi
```cpp
const char* ssid = "TU_WIFI_SSID";
const char* password = "TU_WIFI_PASSWORD";
```

#### MQTT (IP de tu Raspberry Pi)
```cpp
const char* mqtt_server = "192.168.1.100";
const int mqtt_port = 1883;
```

#### IDs únicos
- **Sensor**: Cambia `sensor_id` para cada sensor
- **Actuador**: Cambia `actuator_id` para cada actuador

### 3. Hardware

#### Sensor (sensor_mqtt)
- **ESP32/ESP8266**
- **DHT22** conectado al pin definido en `DHT_PIN`
- **Alimentación 3.3V/5V**

#### Actuador (actuator_mqtt)
- **ESP32/ESP8266**
- **Módulo relé** conectado al pin definido en `RELAY_PIN`
- **LED indicador** (opcional, usa LED_BUILTIN)

### 4. Compilación

1. Abre Arduino IDE
2. Instala librerías necesarias:
   - `PubSubClient`
   - `ArduinoJson`
   - `DHT sensor library`
3. Selecciona tu placa (ESP32 Dev Module / NodeMCU 1.0)
4. Compila y sube el código

## Seguridad

- Los archivos `config.h` están en `.gitignore` y **NO se suben al repositorio**
- Mantén siempre actualizado el archivo `.example` como referencia
- No compartas tus credenciales WiFi o configuraciones específicas

## Topics MQTT

### Sensor
- **Datos**: `home/sensors/{sensor_id}/data`
- **Estado**: `home/sensors/{sensor_id}/status`

### Actuador
- **Comandos**: `home/heating/control`
- **Estado**: `home/heating/status`
- **Estado actuador**: `home/actuators/{actuator_id}/status`

## Troubleshooting

### Problemas de conexión WiFi
1. Verifica SSID y password
2. Comprueba que el ESP esté en rango
3. Revisa la configuración de red

### Problemas MQTT
1. Verifica la IP del servidor MQTT
2. Comprueba que mosquitto esté funcionando
3. Revisa los topics en el bridge

### Sensor DHT22
1. Verifica las conexiones
2. Comprueba el pin configurado
3. Revisa la alimentación del sensor