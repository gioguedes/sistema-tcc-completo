// Teste do buzzer (GPIO12) e do LED de status (GPIO13) com feedback no OLED.
// Alterna os dois sons que o firmware integrado vai usar:
// 1 bip curto (caiu offline, LED aceso) e 2 bips (erro de sensor, LED apagado).
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const int PIN_BUZZER = 12;
const int PIN_LED    = 13;
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void mostrar(const char* som) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("TESTE BUZZER (GPIO12)");
  display.setTextSize(2);
  display.setCursor(0, 25);
  display.println(som);
  display.display();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  Wire.begin(33, 32);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
}

void loop() {
  Serial.println("1 bip (som de queda offline) + LED aceso");
  mostrar("1 BIP");
  digitalWrite(PIN_LED, HIGH);
  tone(PIN_BUZZER, 2000, 150);
  delay(2500);

  Serial.println("2 bips (som de erro de sensor) + LED apagado");
  mostrar("2 BIPS");
  digitalWrite(PIN_LED, LOW);
  tone(PIN_BUZZER, 1200, 120);
  delay(250);
  tone(PIN_BUZZER, 1200, 120);
  delay(2500);
}
