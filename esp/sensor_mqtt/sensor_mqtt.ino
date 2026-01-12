/*
 * Sensor de Temperatura y Humedad para Home Control
 * Compatible con ESP8266/ESP32 + DHT22
 * Envía datos via MQTT a Raspberry Pi
 */

#include <ESP8266WiFi.h>          // Para ESP32
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

// Variables de timing
unsigned long lastMeasurement = 0;
unsigned long lastStatus = 0;
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

void setup() {
  Serial.begin(115200);
  Serial.println("Iniciando sensor Home Control...");
  
  // Habilitar watchdog hardware (8 segundos timeout)
  ESP.wdtDisable();
  ESP.wdtEnable(8000); // 8 segundos timeout
  
  // Leer contador de fallos desde EEPROM (simulado con RTC memory)
  ESP.rtcUserMemoryRead(0, (uint32_t*) &bootFailureCount, sizeof(bootFailureCount));
  if (bootFailureCount > MAX_BOOT_FAILURES) {
    bootFailureCount = 0; // Reset si es demasiado alto
  }
  
  Serial.printf("Intento de arranque #%d\n", bootFailureCount + 1);
  
  // Configurar WiFi con timeouts
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);  // No guardar configuración en flash
  
  // Inicializar DHT
  dht.begin();
  
  // Conectar WiFi con manejo de fallos mejorado
  if (!setup_wifi()) {
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
  
  Serial.println("Sensor configurado y listo!");
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
    
    // Enviar datos de sensor solo si MQTT está conectado
    if (client.connected() && (now - lastMeasurement > measurementInterval)) {
      sendSensorData();
      lastMeasurement = now;
    }
  }
  
  // Peligro de desbordamiento
  if (now >= overflowRestart){
    Serial.println("Reiniciando por desbordamiento de millis()");
    delay(10000);
    ESP.restart();
  }

  // Reiniciar si hay demasiados fallos MQTT consecutivos
  if (mqttFailedAttempts > MAX_MQTT_FAILURES) {
    Serial.println("Demasiados fallos MQTT, reiniciando...");
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

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado. Reintentando...");
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
  // No intentar reconectar si WiFi no está disponible
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  Serial.print("Intentando conexión MQTT...");
  
  String clientId = "ESP8266Client-" + String(sensor_id);
  
  if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
    Serial.println("conectado");
    
    // Suscribirse a comandos (opcional)
    String command_topic = "home/sensors/" + String(sensor_id) + "/command";
    client.subscribe(command_topic.c_str());
    
    mqttFailedAttempts = 0; // Resetear contador de fallos
    
  } else {
    mqttFailedAttempts++;
    Serial.print("falló, rc=");
    Serial.print(client.state());
    Serial.printf(" (intento %d/%d)\n", mqttFailedAttempts, MAX_MQTT_FAILURES);
  }
}

void sendSensorData() {
  float humidity = 0.0;
  float temperature = 0.0;
  bool sensorError = false;

  // Alimentar watchdog antes de lecturas del sensor
  ESP.wdtFeed();
  
  // Leer sensor DHT22 con múltiples intentos
  for(int i = 0; i < 3; ++i){
    humidity = dht.readHumidity();
    temperature = dht.readTemperature();
    
    // Si la lectura es válida, salir del bucle
    if (!isnan(humidity) && !isnan(temperature)) {
      break;
    }
    delay(100); // Pequeña pausa entre lecturas
    ESP.wdtFeed(); // Alimentar watchdog entre intentos
  }
  
  // Verificar si la lectura falló después de todos los intentos
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Error leyendo sensor DHT después de 3 intentos!");
    sensorError = true;
    return;
  }
  
  sensorError = false;
  uint32_t freeHeap = ESP.getFreeHeap();
  
  // Crear JSON con los datos
  StaticJsonDocument<200> doc;
  doc["sensor_id"] = sensor_id;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["timestamp"] = millis();
  doc["wifi_signal"] = WiFi.RSSI();
  doc["free_heap"] = freeHeap;
  doc["sensor_error"] = sensorError;
  doc["mqtt_failures"] = mqttFailedAttempts;
  doc["wifi_reconnects"] = wifiReconnectCount;
  
  // Serializar y enviar
  String jsonString;
  serializeJson(doc, jsonString);
  String topic_data = "home/sensors/livingroom/data";
  
  bool published = false;
  // Intentar publicar con reintentos
  for (int attempt = 0; attempt < 3; attempt++) {
    ESP.wdtFeed(); // Alimentar watchdog antes de cada intento
    if (client.publish(topic_data.c_str(), jsonString.c_str())) {
      Serial.printf("Datos enviados (intento %d): T=%.2f°C, H=%.2f%%, Heap=%d\n", 
                   attempt + 1, temperature, humidity, freeHeap);
      published = true;
      break;
    }
    delay(500); // Pausa entre intentos
  }
  
  if (!published) {
    Serial.println("Error enviando datos MQTT después de 3 intentos");
    mqttFailedAttempts++;
  }

  // Reinicia el sensor si queda poca memoria
  if (freeHeap < 5000){
    Serial.printf("Memoria baja (%d bytes), reiniciando...\n", freeHeap);
    delay(10000);
    ESP.restart();
  }
  
  // Fragmentación de memoria - reiniciar periódicamente
  if (millis() > 86400000) { // 24 horas
    Serial.println("Reinicio preventivo después de 24 horas");
    delay(5000);
    ESP.restart();
  }
  
  // Reinicio de emergencia si nunca se conecta MQTT
  static unsigned long startTime = millis();
  if (!client.connected() && (millis() - startTime > 1800000)) { // 30 minutos
    Serial.println("Sin conexión MQTT por 30 minutos, reiniciando para reconectar WiFi...");
    delay(5000);
    ESP.restart();
  }
}

