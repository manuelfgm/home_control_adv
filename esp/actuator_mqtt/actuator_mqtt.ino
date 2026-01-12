/*
 * Actuador de Calefacción para Home Control
 * Compatible con ESP8266/ESP32 + Relé
 * Recibe comandos via MQTT desde Raspberry Pi
 */

#include <ESP8266WiFi.h>          // Para ESP32
// #include <ESP8266WiFi.h>  // Para ESP8266
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"        // Archivo de configuración

// Clientes
WiFiClient espClient;
PubSubClient client(espClient);

// Variables de estado
bool heating_on = false;
float temperature = 0.0;
unsigned long lastStatus = 0;
unsigned long heatingStartTime = 0;
bool emergencyShutoff = false;

// Variables de timing y control
unsigned long lastWiFiCheck = 0;
unsigned long lastMQTTAttempt = 0;

// Contadores de errores
int mqttFailedAttempts = 0;
int wifiReconnectCount = 0;
int bootFailureCount = 0;  // Contador de fallos de arranque

// Configuraciones de timeout
const unsigned long WIFI_CHECK_INTERVAL = 60000;    // Verificar WiFi cada minuto
const unsigned long MQTT_RETRY_INTERVAL = 30000;    // Reintentar MQTT cada 30 segundos
const unsigned long MAX_RECONNECT_TIME = 300000;    // 5 minutos máximo reconectando
const int MAX_MQTT_FAILURES = 5;                    // Máximo 5 fallos antes de reiniciar
const int MAX_BOOT_FAILURES = 10;                   // Máximo 10 fallos de arranque consecutivos

String topic_command = "home/actuator/boiler/command";
String topic_status = "home/actuator/boiler/data";

void setup() {
  Serial.begin(115200);
  Serial.println("Iniciando actuador de calefacción...");
  
  // Habilitar watchdog hardware (8 segundos timeout)
  ESP.wdtDisable();
  ESP.wdtEnable(8000); // 8 segundos timeout
  
  // Leer contador de fallos desde EEPROM (simulado con RTC memory)
  ESP.rtcUserMemoryRead(0, (uint32_t*) &bootFailureCount, sizeof(bootFailureCount));
  if (bootFailureCount > MAX_BOOT_FAILURES) {
    bootFailureCount = 0; // Reset si es demasiado alto
  }
  
  Serial.printf("Intento de arranque #%d\n", bootFailureCount + 1);
  
  // Configurar pines
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);  // Relé apagado inicialmente
  digitalWrite(LED_PIN, HIGH);
  
  // Configurar WiFi con timeouts
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);  // No guardar configuración en flash
  
  // Conectar WiFi con manejo de fallos mejorado
  if (!setup_wifi()) {
    // CRÍTICO: Asegurar que calefacción esté apagada si no hay WiFi
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
    
    bootFailureCount++;
    ESP.rtcUserMemoryWrite(0, (uint32_t*) &bootFailureCount, sizeof(bootFailureCount));
    
    // Pausa progresiva: más tiempo entre reintentos
    unsigned long delayTime = min(bootFailureCount * 30000UL, 300000UL); // 30s a 5min máximo
    Serial.printf("Fallo WiFi #%d, esperando %lu segundos antes de reiniciar...\n", 
                 bootFailureCount, delayTime / 1000);
    
    delay(delayTime);
    ESP.restart();
  }
  
  // WiFi conectado exitosamente - reset contador
  bootFailureCount = 0;
  ESP.rtcUserMemoryWrite(0, (uint32_t*) &bootFailureCount, sizeof(bootFailureCount));
  
  // Configurar MQTT con timeouts más conservadores
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setKeepAlive(60);     // Keepalive de 60 segundos
  client.setSocketTimeout(30); // Timeout de socket de 30 segundos
  
  Serial.println("Actuador configurado y listo!");
  ESP.wdtFeed(); // Alimentar watchdog después del setup
}

void loop() {
  // Alimentar watchdog hardware al inicio del loop
  ESP.wdtFeed();
  
  unsigned long now = millis();
  
  // Verificar conexión WiFi periódicamente
  if (now - lastWiFiCheck > WIFI_CHECK_INTERVAL) {
    checkWiFiConnection();
    lastWiFiCheck = now;
  }
  
  // Mantener conexión MQTT solo si WiFi está conectado
  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) {
      // Limitar intentos de reconexión MQTT
      if (now - lastMQTTAttempt > MQTT_RETRY_INTERVAL) {
        reconnect();
        lastMQTTAttempt = now;
      }
    } else {
      client.loop();
      mqttFailedAttempts = 0; // Resetear contador de fallos
    }
    
    // Enviar estado solo si MQTT está conectado
    if (client.connected() && (now - lastStatus > statusInterval)) {
      sendStatus();
      lastStatus = now;
    }
  }

  // Seguridad
  safetyCheck();
  
  // Reiniciar si hay demasiados fallos MQTT consecutivos
  if (mqttFailedAttempts > MAX_MQTT_FAILURES) {
    Serial.println("Demasiados fallos MQTT, reiniciando...");
    // Apagar calefacción antes de reiniciar por seguridad
    turnHeatingOff();
    delay(5000);
    ESP.restart();
  }
  
  // Alimentar watchdog antes del delay
  ESP.wdtFeed();
  delay(1000);
}

bool setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  
  // Timeout para evitar bloqueo infinito
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 60) { // Aumentado a 60 intentos
    delay(1000);
    ESP.wdtFeed(); // Alimentar watchdog durante la espera
    Serial.print(".");
    attempts++;
    
    // Cada 30 segundos, reintentar la conexión
    if (attempts % 30 == 0 && attempts < 60) {
      Serial.println();
      Serial.println("Reintentando conexión WiFi...");
      WiFi.disconnect();
      delay(2000);
      WiFi.begin(ssid, password);
    }
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi conectado exitosamente");
    Serial.println("IP: ");
    Serial.println(WiFi.localIP());
    Serial.printf("Señal WiFi: %d dBm\n", WiFi.RSSI());
    return true;
  } else {
    Serial.println("");
    Serial.println("Error: No se pudo conectar al WiFi después de 60 segundos");
    return false;
  }
}

void turnHeatingOn() {
  if (!heating_on) {
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    heating_on = true;
    Serial.println("Calefacción ENCENDIDA");
  }
}

void turnHeatingOff() {
  if (heating_on) {
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
    heating_on = false;
    Serial.println("Calefacción APAGADA");
  }
}

void sendStatus() {
  // Alimentar watchdog antes de envío
  ESP.wdtFeed();
  
  // Estado del actuador
  uint32_t freeHeap = ESP.getFreeHeap();
  
  StaticJsonDocument<300> actuator_doc;
  actuator_doc["actuator_id"] = actuator_id;
  actuator_doc["is_heating"] = heating_on;
  actuator_doc["timestamp"] = millis();
  actuator_doc["wifi_signal"] = WiFi.RSSI();
  actuator_doc["free_heap"] = freeHeap;
  actuator_doc["temperature"] = temperature;
  actuator_doc["mqtt_failures"] = mqttFailedAttempts;
  actuator_doc["wifi_reconnects"] = wifiReconnectCount;
  
  String actuator_json;
  serializeJson(actuator_doc, actuator_json);
  
  bool published = false;
  // Intentar publicar con reintentos
  for (int attempt = 0; attempt < 3; attempt++) {
    ESP.wdtFeed(); // Alimentar watchdog antes de cada intento
    if (client.publish(topic_status.c_str(), actuator_json.c_str())) {
      Serial.printf("Estado enviado (intento %d): Heating=%s, Heap=%d\n", 
                   attempt + 1, heating_on ? "ON" : "OFF", freeHeap);
      published = true;
      break;
    }
    delay(500); // Pausa entre intentos
  }
  
  if (!published) {
    Serial.println("Error enviando estado después de 3 intentos");
    mqttFailedAttempts++;
  }

  // Reinicia el actuador si queda poca memoria
  if (freeHeap < 5000){
    Serial.printf("Memoria baja (%d bytes), apagando calefacción y reiniciando...\n", freeHeap);
    turnHeatingOff(); // Seguridad antes de reiniciar
    delay(10000);
    ESP.restart();
  }
  
  // Fragmentación de memoria - reiniciar periódicamente
  if (millis() > 86400000) { // 24 horas
    Serial.println("Reinicio preventivo después de 24 horas");
    turnHeatingOff(); // Seguridad antes de reiniciar
    delay(5000);
    ESP.restart();
  }
  
  // Reinicio de emergencia si nunca se conecta MQTT (MUY CRÍTICO para actuador)
  static unsigned long startTime = millis();
  if (!client.connected() && (millis() - startTime > 1800000)) { // 30 minutos
    Serial.println("Sin conexión MQTT por 30 minutos, apagando calefacción y reiniciando...");
    turnHeatingOff(); // SEGURIDAD CRÍTICA
    delay(10000); // Dar tiempo para que se apague
    ESP.restart();
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
  
  temperature = doc["temperature"];
  String action = doc["action"];

  // Evitar Temperatura máxima
  if (temperature >= emergencyShutoffTemp){
    turnHeatingOff();
  } else{
    // Extraer acción
    if (action == "turn_on") {
      turnHeatingOn();
    } else if (action == "turn_off") {
      turnHeatingOff();
    }
  }

  // Enviar confirmación
  sendStatus();
  lastStatus = millis();
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

void reconnect() {
  // No intentar reconectar si WiFi no está disponible
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  Serial.print("Intentando conexión MQTT...");
  
  String clientId = "HeatingActuator-" + String(actuator_id);
  
  if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
    Serial.println("conectado");
    
    // Suscribirse a comandos de calefacción
    client.subscribe(topic_command.c_str());
    Serial.printf("Suscrito a: %s\n", topic_command.c_str());
    
    mqttFailedAttempts = 0; // Resetear contador de fallos
    
  } else {
    mqttFailedAttempts++;
    Serial.print("falló, rc=");
    Serial.print(client.state());
    Serial.printf(" (intento %d/%d)\n", mqttFailedAttempts, MAX_MQTT_FAILURES);
    
    // Apagar calefacción por seguridad si falla MQTT
    if (mqttFailedAttempts > 2 && heating_on) {
      Serial.println("Múltiples fallos MQTT - apagando calefacción por seguridad");
      turnHeatingOff();
    }
  }
}


// Función de seguridad mejorada - apagar calefacción si pierde conexión
void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado - apagando calefacción por seguridad");
    turnHeatingOff();
    wifiReconnectCount++;
    
    WiFi.disconnect();
    delay(1000);
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      ESP.wdtFeed(); // Alimentar watchdog durante reconexión
      attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("WiFi reconectado exitosamente");
      wifiReconnectCount = 0;
    } else {
      Serial.println("Fallo reconexión WiFi");
      if (wifiReconnectCount > 3) {
        Serial.println("Demasiados fallos WiFi, reiniciando...");
        delay(5000);
        ESP.restart();
      }
    }
  }
}

// Llamar en el loop para mayor seguridad
void safetyCheck() {
  static unsigned long lastSafetyCheck = 0;
  unsigned long now = millis();
  
  if (now - lastSafetyCheck > 60000) { // Cada 60 segundos
    // Solo verificar WiFi si no se hizo recientemente
    if (now - lastWiFiCheck > WIFI_CHECK_INTERVAL - 5000) {
      if (WiFi.status() != WL_CONNECTED && heating_on) {
        Serial.println("WiFi desconectado - apagando calefacción por seguridad");
        turnHeatingOff();
      }
    }
    
    // Verificar si no hemos recibido comandos en mucho tiempo
    if (!client.connected() && heating_on) {
      Serial.println("MQTT desconectado - apagando calefacción por seguridad");
      turnHeatingOff();
    }
    
    // Verificar temperatura de emergencia
    if (temperature >= emergencyShutoffTemp && heating_on) {
      Serial.printf("Temperatura de emergencia alcanzada (%.2f°C) - apagando\n", temperature);
      turnHeatingOff();
      emergencyShutoff = true;
    }
    
    lastSafetyCheck = now;
  }

  // Peligro de desbordamiento
  if (now >= overflowRestart){
    Serial.println("Reiniciando por desbordamiento de millis()");
    turnHeatingOff(); // Seguridad antes de reiniciar
    delay(10000);
    ESP.restart();
  }
}
