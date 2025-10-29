/*
 * Actuador de Calefacción para Home Control
 * Compatible con ESP8266/ESP32 + Relé
 * Recibe comandos via MQTT desde Raspberry Pi
 */

#include <WiFi.h>          // Para ESP32
// #include <ESP8266WiFi.h>  // Para ESP8266
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"        // Archivo de configuración

// Clientes
WiFiClient espClient;
PubSubClient client(espClient);

// Variables de estado
bool heating_on = false;
float target_temperature = 20.0;
unsigned long lastStatus = 0;
unsigned long heatingStartTime = 0;
bool emergencyShutoff = false;

void setup() {
  Serial.begin(115200);
  Serial.println("Iniciando actuador de calefacción...");
  
  // Configurar pines
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // Relé apagado inicialmente
  digitalWrite(LED_PIN, LOW);
  
  // Conectar WiFi
  setup_wifi();
  
  // Configurar MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  Serial.println("Actuador configurado y listo!");
}

void loop() {
  // Mantener conexión MQTT
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  unsigned long now = millis();
  
  // Enviar estado cada minuto
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
  Serial.print("Mensaje recibido [");
  Serial.print(topic);
  Serial.print("] ");
  
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);
  
  // Procesar comando si es para calefacción
  if (String(topic) == topic_command) {
    processHeatingCommand(message);
  }
}

void processHeatingCommand(String message) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("Error parseando JSON: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Extraer acción
  String action = doc["action"];
  
  if (action == "turn_on") {
    turnHeatingOn();
    if (doc.containsKey("target_temperature")) {
      target_temperature = doc["target_temperature"];
    }
  } else if (action == "turn_off") {
    turnHeatingOff();
  } else if (action == "set_temperature") {
    if (doc.containsKey("target_temperature")) {
      target_temperature = doc["target_temperature"];
      Serial.printf("Temperatura objetivo establecida: %.1f°C\n", target_temperature);
    }
  }
  
  // Enviar confirmación
  sendStatus();
}

void turnHeatingOn() {
  if (!heating_on) {
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
    heating_on = true;
    Serial.println("Calefacción ENCENDIDA");
  }
}

void turnHeatingOff() {
  if (heating_on) {
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    heating_on = false;
    Serial.println("Calefacción APAGADA");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT...");
    
    String clientId = "HeatingActuator-" + String(actuator_id);
    
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("conectado");
      
      // Suscribirse a comandos de calefacción
      client.subscribe(topic_command.c_str());
      Serial.printf("Suscrito a: %s\n", topic_command.c_str());
      
      // Enviar estado inicial
      sendStatus();
      
    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      Serial.println(" reintentando en 5 segundos");
      delay(5000);
    }
  }
}

void sendStatus() {
  // Estado del actuador
  StaticJsonDocument<300> actuator_doc;
  actuator_doc["actuator_id"] = actuator_id;
  actuator_doc["online"] = true;
  actuator_doc["heating_on"] = heating_on;
  actuator_doc["wifi_signal"] = WiFi.RSSI();
  actuator_doc["free_heap"] = ESP.getFreeHeap();
  actuator_doc["uptime"] = millis();
  actuator_doc["ip_address"] = WiFi.localIP().toString();
  
  String actuator_json;
  serializeJson(actuator_doc, actuator_json);
  
  if (client.publish(topic_actuator_status.c_str(), actuator_json.c_str())) {
    Serial.println("Estado del actuador enviado");
  }
  
  // Estado de calefacción para Django
  StaticJsonDocument<200> heating_doc;
  heating_doc["is_heating"] = heating_on;
  heating_doc["target_temperature"] = target_temperature;
  heating_doc["mode"] = "mqtt_control";
  heating_doc["timestamp"] = millis();
  heating_doc["source"] = actuator_id;
  
  String heating_json;
  serializeJson(heating_doc, heating_json);
  
  if (client.publish(topic_status.c_str(), heating_json.c_str())) {
    Serial.println("Estado de calefacción enviado");
  }
}

// Función de seguridad - apagar calefacción si pierde conexión
void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado - apagando calefacción por seguridad");
    turnHeatingOff();
  }
}

// Llamar en el loop para mayor seguridad
void safetyCheck() {
  static unsigned long lastSafetyCheck = 0;
  unsigned long now = millis();
  
  if (now - lastSafetyCheck > 10000) { // Cada 10 segundos
    checkWiFiConnection();
    
    // Verificar si no hemos recibido comandos en mucho tiempo
    if (!client.connected() && heating_on) {
      Serial.println("MQTT desconectado - apagando calefacción por seguridad");
      turnHeatingOff();
    }
    
    lastSafetyCheck = now;
  }
}