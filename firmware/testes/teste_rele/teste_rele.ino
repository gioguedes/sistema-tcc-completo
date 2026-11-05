// Teste isolado do modulo rele (GPIO26). Alterna a cada 3 s; ouvir o clique.
// OLED opcional: se nao estiver conectado, o teste funciona so pelo Serial.
// Modulo validado em 2026-07-09: ATIVO-BAIXO (arma em LOW) e alimentado em 3V3.
// Com VCC em 5V o HIGH de 3,3V do ESP32 nao desarma o rele — manter VCC no 3V3.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const int PIN_RELE = 26;
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void mostrar(const char* estado) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("TESTE RELE (GPIO26)");
  display.setTextSize(2);
  display.setCursor(0, 25);
  display.println(estado);
  display.display();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_RELE, OUTPUT);
  digitalWrite(PIN_RELE, HIGH);  // HIGH = desarmado (modulo ativo-baixo)
  Wire.begin(33, 32);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
}

void loop() {
  digitalWrite(PIN_RELE, HIGH);
  Serial.println("Saida GPIO26 = HIGH");
  mostrar("HIGH");
  delay(3000);
  digitalWrite(PIN_RELE, LOW);
  Serial.println("Saida GPIO26 = LOW");
  mostrar("LOW");
  delay(3000);
}
