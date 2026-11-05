// Teste isolado do sensor de turbidez (GPIO34, atras de divisor 4,7k + 4,7k).
// Mostra a tensao REAL de saida do sensor (ja corrigida pelo fator do divisor).
// OLED opcional: se nao estiver conectado, o teste funciona so pelo Serial.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const int   PIN_TURBIDEZ  = 34;
const float FATOR_DIVISOR = 2.0;  // divisor 4,7k (cima) + 4,7k (baixo): no exato = metade da tensao
const int   N_AMOSTRAS    = 32;

Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
  Serial.begin(115200);
  analogSetPinAttenuation(PIN_TURBIDEZ, ADC_11db);
  Wire.begin(33, 32);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
}

void loop() {
  uint32_t soma = 0;
  for (int i = 0; i < N_AMOSTRAS; i++) {
    soma += analogReadMilliVolts(PIN_TURBIDEZ);
    delay(2);
  }
  float mv = (soma / (float)N_AMOSTRAS) * FATOR_DIVISOR;

  Serial.printf("Tensao real do sensor: %.0f mV\n", mv);

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("TESTE TURBIDEZ");
  display.setTextSize(2);
  display.setCursor(0, 25);
  display.print(mv, 0);
  display.println(" mV");
  display.display();
  delay(500);
}
