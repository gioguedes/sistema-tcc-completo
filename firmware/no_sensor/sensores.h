// Leitura dos tres sensores com media de amostras e conversao por calibracao.
// NAN em qualquer campo significa falha de leitura daquele sensor: o publicador
// converte NAN em null no JSON (criterio de aceite 4 da spec).
#ifndef SENSORES_H
#define SENSORES_H

#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <math.h>
#include <time.h>
#include "config.h"

struct Leitura {
  time_t ts;
  float  ph;
  float  temperatura;
  float  turbidez;
};

static OneWire sensOneWire(PIN_DS18B20);
static DallasTemperature sensDs18b20(&sensOneWire);
const int N_AMOSTRAS_ADC = 32;
// 12 bits = 0,0625 C de passo, 750 ms de conversao. Precisa casar com o que a
// biblioteca espera (ver sensoresIniciar).
const uint8_t DS18B20_RESOLUCAO_BITS = 12;

// Tensao media no pino, em mV (ja convertida pela curva de fabrica do ADC).
inline float lerMediaMilliVolts(int pino) {
  uint32_t soma = 0;
  for (int i = 0; i < N_AMOSTRAS_ADC; i++) {
    soma += analogReadMilliVolts(pino);
    delayMicroseconds(200);
  }
  return soma / (float)N_AMOSTRAS_ADC;
}

inline void sensoresIniciar() {
  analogSetPinAttenuation(PIN_PH, ADC_11db);
  analogSetPinAttenuation(PIN_TURBIDEZ, ADC_11db);
  sensDs18b20.begin();
  // Fixar a resolucao e obrigatorio, nao cosmetico: sem isso a biblioteca
  // assume 9 bits e espera ~94 ms pela conversao, enquanto o sensor esta em
  // 12 bits e leva 750 ms. O scratchpad e lido no meio da conversao, o CRC
  // falha e a leitura volta -127 (diagnosticado na bancada em 17/08).
  sensDs18b20.setResolution(DS18B20_RESOLUCAO_BITS);
}

inline float lerTemperatura() {
  sensDs18b20.requestTemperatures();
  float t = sensDs18b20.getTempCByIndex(0);
  // -127 (DEVICE_DISCONNECTED_C) e 85 (valor de power-on nunca convertido)
  // sao os dois sintomas classicos de sensor solto no barramento 1-Wire.
  if (t == DEVICE_DISCONNECTED_C || t < -40.0f || t >= 85.0f) return NAN;
  return t;
}

inline float lerPh() {
  float mv = lerMediaMilliVolts(PIN_PH);
  if (mv < PH_MV_MIN || mv > PH_MV_MAX) return NAN;  // BNC solto / cabo desligado
  float slope = (PH_CAL_PH2 - PH_CAL_PH1) / (PH_CAL_MV2 - PH_CAL_MV1);
  float ph = PH_CAL_PH1 + (mv - PH_CAL_MV1) * slope;
  if (ph < 0.0f || ph > 14.0f) return NAN;
  return ph;
}

inline float lerTurbidez() {
  float mv = lerMediaMilliVolts(PIN_TURBIDEZ) * TURB_FATOR_DIVISOR;
  if (mv < TURB_MV_MIN_VALIDO) return NAN;  // sensor ausente: divisor puxa o no para 0 V
  float ntu = (TURB_MV_0NTU - mv) * 100.0f / (TURB_MV_0NTU - TURB_MV_100NTU);
  if (ntu < 0.0f) ntu = 0.0f;  // agua mais limpa que a referencia de 0 NTU
  return ntu;
}

inline Leitura sensoresLer() {
  Leitura l;
  l.ts          = time(nullptr);
  l.temperatura = lerTemperatura();
  l.ph          = lerPh();
  l.turbidez    = lerTurbidez();
  return l;
}

// Leitura vazia para o estado inicial, antes do primeiro ciclo.
inline Leitura leituraVazia() {
  Leitura l;
  l.ts = 0;
  l.ph = l.temperatura = l.turbidez = NAN;
  return l;
}

#endif
