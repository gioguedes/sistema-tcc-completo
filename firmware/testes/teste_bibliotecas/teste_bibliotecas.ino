// Verifica que todas as bibliotecas do projeto compilam juntas no core ESP32.
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include <MQTT.h>

void setup() {
  Serial.begin(115200);
  Serial.println("Bibliotecas OK");
}

void loop() {}
