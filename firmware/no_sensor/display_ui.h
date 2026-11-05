// Interface local: OLED, LED de status e buzzer (tabela de estados da spec, secao 6.5).
#ifndef DISPLAY_UI_H
#define DISPLAY_UI_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <math.h>
#include "config.h"
#include "sensores.h"

enum ModoLed { LED_FIXO, LED_PISCA_LENTO, LED_PISCA_RAPIDO };

static Adafruit_SSD1306 uiDisplay(128, 64, &Wire, -1);
static bool uiTemDisplay = false;

// Um display() manda 1 kB pelo I2C. A 100 kHz isso custa ~90 ms e engasga o laco
// principal (o LED chega a piscar torto); a 400 kHz cai para ~25 ms. Somado ao
// limite de redesenho abaixo, a UI ocupa ~5% do tempo do laco.
const uint32_t UI_INTERVALO_REDESENHO_MS = 500;
static uint32_t uiUltimoRedesenhoMs = 0;

inline void uiIniciar() {
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
  Wire.setClock(400000);
  uiTemDisplay = uiDisplay.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  if (!uiTemDisplay) {
    Serial.println("AVISO: OLED nao respondeu no endereco 0x3C (segue so pelo Serial)");
    return;
  }
  uiDisplay.clearDisplay();
  uiDisplay.display();
}

inline void uiBipCurto() { tone(PIN_BUZZER, 2000, 100); }

inline void uiBipDuplo() {
  tone(PIN_BUZZER, 1500, 100);
  delay(150);
  tone(PIN_BUZZER, 1500, 100);
}

inline void uiLed(ModoLed modo) {
  switch (modo) {
    case LED_FIXO:         digitalWrite(PIN_LED, HIGH); break;
    case LED_PISCA_LENTO:  digitalWrite(PIN_LED, (millis() / 700) % 2); break;
    case LED_PISCA_RAPIDO: digitalWrite(PIN_LED, (millis() / 200) % 2); break;
  }
}

// Autoteste de boot: pisca o LED 3x e le o nivel do pino de volta. Em pino
// configurado como saida, digitalRead() no ESP32 devolve o nivel real do pino,
// entao a divergencia entre o que se escreve e o que se le denuncia quem esta
// sobrescrevendo a configuracao.
// Diz se o LED continua no circuito, sem depender de inspecao visual.
// Com pull-up interno (~45 k) e um LED (Vf ~1,8 V) em serie com 330R ate o
// terra, o pino fica em ~1,8 V, abaixo do limiar de nivel alto (2,48 V), e le 0.
// Circuito aberto (LED ou resistor fora do furo) le 1, seguindo o pull.
inline void uiChecarLed() {
  pinMode(PIN_LED, INPUT_PULLUP);
  delay(5);
  int comUp = digitalRead(PIN_LED);
  pinMode(PIN_LED, INPUT_PULLDOWN);
  delay(5);
  int comDown = digitalRead(PIN_LED);
  pinMode(PIN_LED, OUTPUT);
  Serial.printf("  continuidade do LED: pull-up=%d pull-down=%d -> ", comUp, comDown);
  Serial.println(comUp == 0 ? "LED NO CIRCUITO (caminho ate o terra existe)"
                            : "CIRCUITO ABERTO (LED ou resistor fora do furo)");
}

// Acende o LED fixo por 3 s, reproduzindo a condicao do teste_buzzer, que
// acendia. Pisca de 0,7 s pode passar batido; 3 s aceso, nao.
inline void uiLedFixoPorSegundos(int segundos) {
  Serial.printf("  LED aceso fixo por %d s -- OLHE A BANCADA AGORA", segundos);
  Serial.println();
  digitalWrite(PIN_LED, HIGH);
  delay(segundos * 1000);
  digitalWrite(PIN_LED, LOW);
  Serial.println("  LED apagado.");
}

inline void uiAutotesteLed(const char* quando) {
  Serial.printf("  autoteste do LED (%s):", quando);
  for (int i = 0; i < 3; i++) {
    digitalWrite(PIN_LED, HIGH);
    int lidoAlto = digitalRead(PIN_LED);
    delay(250);
    digitalWrite(PIN_LED, LOW);
    int lidoBaixo = digitalRead(PIN_LED);
    delay(250);
    Serial.printf(" [escrevi 1 li %d / escrevi 0 li %d]", lidoAlto, lidoBaixo);
  }
  Serial.println();
}

// Imprime "rotulo: valor unidade" ou "rotulo: ERRO" quando o sensor falhou (NAN).
inline void uiLinhaGrandeza(const char* rotulo, float valor, int casas, const char* unidade) {
  uiDisplay.print(rotulo);
  if (isnan(valor)) {
    uiDisplay.println("ERRO");
  } else {
    uiDisplay.print(valor, casas);
    uiDisplay.println(unidade);
  }
}

inline void uiMostrar(const char* status, const Leitura& ultima, int emBuffer, bool temLeitura) {
  if (!uiTemDisplay) return;
  uint32_t agora = millis();
  if (uiUltimoRedesenhoMs != 0 && agora - uiUltimoRedesenhoMs < UI_INTERVALO_REDESENHO_MS) return;
  uiUltimoRedesenhoMs = agora;

  uiDisplay.clearDisplay();
  uiDisplay.setTextColor(SSD1306_WHITE);
  uiDisplay.setTextSize(1);
  uiDisplay.setCursor(0, 0);
  uiDisplay.println("--- NO SENSOR ---");

  uiDisplay.setCursor(0, 12);
  uiDisplay.print(status);
  if (emBuffer > 0) {
    uiDisplay.print(" (");
    uiDisplay.print(emBuffer);
    uiDisplay.print(" buf.)");
  }
  uiDisplay.println();

  if (temLeitura) {
    uiDisplay.setCursor(0, 28);
    uiLinhaGrandeza("pH:   ", ultima.ph,          2, "");
    uiLinhaGrandeza("Temp: ", ultima.temperatura, 1, " C");
    uiLinhaGrandeza("Turb: ", ultima.turbidez,    1, " NTU");
  }
  uiDisplay.display();
}

#endif
