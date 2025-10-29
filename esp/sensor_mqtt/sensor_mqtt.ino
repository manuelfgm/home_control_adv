/*
 * Sensor de Temperatura y Humedad para Home Control
 * Compatible con ESP8266/ESP32 + DHT22
 * Envía datos via MQTT a Raspberry Pi
 */

#include <WiFi.h>          // Para ESP32
// #include <ESP8266WiFi.h>  // Para ESP8266
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include "config.h"        // Archivo de configuración

// Configuración del sensor DHT
DHT dht(DHT_PIN, DHT_TYPE);

// Clientes
WiFiClient espClient;
PubSubClient client(espClient);

// Variables de medición
float temperature = 0.0;
float humidity = 0.0;
bool sensorError = false;

// Variables de timing
unsigned long lastMeasurement = 0;
unsigned long lastStatus = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("Iniciando sensor Home Control...");
  
  // Inicializar DHT
  dht.begin();
  
  // Conectar WiFi
  setup_wifi();
  
  // Configurar MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  Serial.println("Sensor configurado y listo!");
}

void loop() {
  // Mantener conexión MQTT
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  unsigned long now = millis();
  
  // Enviar datos de sensor cada 30 segundos
  if (now - lastMeasurement > measurementInterval) {
    sendSensorData();
    lastMeasurement = now;
  }
  
  // Enviar estado cada 5 minutos
  if (now - lastStatus > statusInterval) {
    sendStatus();
    lastStatus = now;
  }
  
  delay(1000);
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("IP: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  // Manejar comandos recibidos (opcional)
  Serial.print("Mensaje recibido [");
  Serial.print(topic);
  Serial.print("] ");
  
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT...");
    
    String clientId = "ESP8266Client-" + String(sensor_id);
    
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("conectado");
      
      // Suscribirse a comandos (opcional)
      String command_topic = "home/sensors/" + String(sensor_id) + "/command";
      client.subscribe(command_topic.c_str());
      
      // Enviar mensaje de conexión
      sendStatus();
      
    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      Serial.println(" reintentando en 5 segundos");
      delay(5000);
    }
  }
}

void sendSensorData() {
  // Leer sensor DHT22
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  
  // Verificar si la lectura falló
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Error leyendo sensor DHT!");
    sensorError = true;
    return;
  }
  
  sensorError = false;
  
  // Crear JSON con los datos
  StaticJsonDocument<200> doc;
  doc["sensor_id"] = sensor_id;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["timestamp"] = millis();
  doc["wifi_signal"] = WiFi.RSSI();
  
  // Serializar y enviar
  String jsonString;
  serializeJson(doc, jsonString);
  
  if (client.publish(topic_data.c_str(), jsonString.c_str())) {
    Serial.printf("Datos enviados: T=%.2f°C, H=%.2f%%\n", temperature, humidity);
  } else {
    Serial.println("Error enviando datos MQTT");
  }
}

void sendStatus() {
  // Crear JSON con el estado del dispositivo
  StaticJsonDocument<300> doc;
  doc["sensor_id"] = sensor_id;
  doc["online"] = true;
  doc["wifi_signal"] = WiFi.RSSI();
  doc["free_heap"] = ESP.getFreeHeap();
  doc["uptime"] = millis();
  doc["sensor_error"] = sensorError;
  doc["ip_address"] = WiFi.localIP().toString();
  
  // Serializar y enviar
  String jsonString;
  serializeJson(doc, jsonString);
  
  if (client.publish(topic_status.c_str(), jsonString.c_str())) {
    Serial.println("Estado enviado");
  } else {
    Serial.println("Error enviando estado MQTT");
  }
}

// Función para enviar comandos de calefacción (si es actuador)
void sendHeatingCommand(bool turn_on, float target_temp) {
  StaticJsonDocument<200> doc;
  doc["action"] = turn_on ? "turn_on" : "turn_off";
  doc["target_temperature"] = target_temp;
  doc["timestamp"] = millis();
  doc["source"] = sensor_id;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  const char* heating_topic = "home/heating/control";
  if (client.publish(heating_topic, jsonString.c_str())) {
    Serial.printf("Comando calefacción enviado: %s\n", turn_on ? "ON" : "OFF");
  }
}