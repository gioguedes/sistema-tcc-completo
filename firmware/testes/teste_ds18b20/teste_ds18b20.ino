// Teste isolado do DS18B20 (1-Wire no GPIO25). Mostra a temperatura no Serial e no OLED.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h>
#include <DallasTemperature.h>

const int PIN_DS18B20 = 25;

Adafruit_SSD1306 display(128, 64, &Wire, -1);
OneWire oneWire(PIN_DS18B20);
DallasTemperature sensores(&oneWire);

void setup() {
  Serial.begin(115200);
  Wire.begin(33, 32);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("Falha ao iniciar o OLED");
  }
  sensores.begin();
  Serial.printf("Dispositivos 1-Wire encontrados: %d\n", sensores.getDeviceCount());
}

void loop() {
  sensores.requestTemperatures();
  float t = sensores.getTempCByIndex(0);

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("TESTE DS18B20");
  display.setTextSize(2);
  display.setCursor(0, 25);
  if (t == DEVICE_DISCONNECTED_C) {
    display.println("ERRO");
    Serial.println("ERRO: sensor nao respondeu");
  } else {
    display.print(t, 1);
    display.println(" C");
    Serial.printf("Temperatura: %.2f C\n", t);
  }
  display.display();
  delay(1000);
}
