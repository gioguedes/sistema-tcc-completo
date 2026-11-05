// Modelo de configuracao do no sensor. Copie para config.h (nao versionado) e preencha.
//   Copy-Item config.example.h config.h
#ifndef CONFIG_H
#define CONFIG_H

// ---- Wi-Fi (ESP32 so opera em 2,4 GHz) ----
#define WIFI_SSID  "SUA_REDE_2G"
#define WIFI_SENHA "SUA_SENHA"

// ---- MQTT ----
#define MQTT_BROKER_IP    "192.168.0.10"  // IPv4 ou hostname do broker (Task 6)
#define MQTT_BROKER_PORTA 1883
// Prefixo do topico: "<prefixo>/<mac>/leituras". No broker local "piscicultura"
// basta; em broker publico use algo unico, senao colide com outros projetos.
#define MQTT_TOPICO_PREFIXO "piscicultura"

// ---- Ciclo de leitura ----
#define INTERVALO_LEITURA_MS 60000UL  // entrega: 60 s. Testes de bancada: 10000UL.

// ---- Pinagem (spec 2026-07-02, secao 4) ----
#define PIN_OLED_SDA 33
#define PIN_OLED_SCL 32
#define PIN_LED      13
#define PIN_BUZZER   12
#define PIN_DS18B20  25
#define PIN_TURBIDEZ 34   // ADC1_CH6 - analogicos so no ADC1 (Wi-Fi desliga o ADC2)
#define PIN_PH       35   // ADC1_CH7
#define PIN_RELE     26

// ---- Rele (validado na Task 3: modulo ATIVO-BAIXO, alimentado em 3V3) ----
// Com VCC em 5 V o HIGH de 3,3 V do ESP32 nao desarma a bobina. Nao mudar para 5 V.
#define RELE_LIGADO    LOW
#define RELE_DESLIGADO HIGH

// ---- Calibracao do pH (docs/calibracao_ph.md) ----
// Calibracao de 2 pontos feita em 26/10/2026 com os tampoes 4,01 e 6,86.
#define PH_CALIBRADO 1
#define PH_CAL_PH1   4.01f
#define PH_CAL_MV1   2077.0f          // tensao no tampao 4,01
#define PH_CAL_PH2   6.86f
#define PH_CAL_MV2   1614.0f          // tensao no tampao 6,86

// Faixa de tensao plausivel do modulo com o eletrodo conectado.
// Fora dela = BNC solto ou cabo desligado -> leitura vira null (na Task 5 o BNC
// solto lia ~300 mV instavel, o que a checagem de 0-14 pH nao pegava).
#define PH_MV_MIN 500.0f
#define PH_MV_MAX 2700.0f

// ---- Turbidez (docs/evidencias/04_turbidez_serial.txt) ----
#define TURB_FATOR_DIVISOR 2.0f     // divisor 4,7k + 4,7k (o no fica com metade da tensao)
#define TURB_MV_0NTU   2656.0f      // medido em agua limpa (02/07, antes da infiltracao)
#define TURB_MV_100NTU 2010.0f      // PROVISORIO: suspensao de referencia ainda nao medida
// Sensor ausente/desligado: o resistor de baixo do divisor puxa o no para ~0 V.
#define TURB_MV_MIN_VALIDO 150.0f   // abaixo disso a leitura vira null

// ---- Buffer offline (CT03) ----
#define BUFFER_CAPACIDADE 120       // ~2 h de leituras a 60 s

// Duracao da queda de rede simulada pelo comando "queda" no Serial. Precisa ser
// maior que 3 x INTERVALO_LEITURA_MS para o CT03 acumular pelo menos 3 leituras;
// derivada do intervalo para a invariante nao quebrar ao alternar 10 s / 60 s.
#define TESTE_QUEDA_REDE_MS (3UL * INTERVALO_LEITURA_MS + 20000UL)

#endif
