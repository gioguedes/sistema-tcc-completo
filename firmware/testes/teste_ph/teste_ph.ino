// Teste e calibracao do sensor de pH SEN0161-V2 (GPIO35).
// Antes da calibracao: usar apenas a leitura de tensao (mV) — o valor de pH
// mostrado usa constantes provisorias e NAO vale nada ate a calibracao.
// Depois: substituir as 4 constantes PH_CAL_* pelos valores medidos nos tampoes.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const int   PIN_PH     = 35;
const int   N_AMOSTRAS = 32;

// ---- CONSTANTES DE CALIBRACAO (substituir apos medir nos tampoes) ----
const float PH_CAL_PH1 = 4.01;
const float PH_CAL_MV1 = 2032.0;  // tensao medida no tampao 4,01
const float PH_CAL_PH2 = 6.86;
const float PH_CAL_MV2 = 1500.0;  // tensao medida no tampao 6,86

Adafruit_SSD1306 display(128, 64, &Wire, -1);

float lerMediaMv() {
  uint32_t soma = 0;
  for (int i = 0; i < N_AMOSTRAS; i++) {
    soma += analogReadMilliVolts(PIN_PH);
    delay(2);
  }
  return soma / (float)N_AMOSTRAS;
}

void setup() {
  Serial.begin(115200);
  analogSetPinAttenuation(PIN_PH, ADC_11db);
  Wire.begin(33, 32);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
}

void loop() {
  float mv = lerMediaMv();
  float slope = (PH_CAL_PH2 - PH_CAL_PH1) / (PH_CAL_MV2 - PH_CAL_MV1);
  float ph = PH_CAL_PH1 + (mv - PH_CAL_MV1) * slope;

  Serial.printf("Tensao: %.0f mV  ->  pH %.2f\n", mv, ph);

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("TESTE pH (GPIO35)");
  display.setCursor(0, 14);
  display.print(mv, 0);
  display.println(" mV");
  display.setTextSize(2);
  display.setCursor(0, 32);
  display.print("pH ");
  display.println(ph, 2);
  display.display();
  delay(500);
}
