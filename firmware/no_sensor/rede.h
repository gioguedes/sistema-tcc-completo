// Conectividade: Wi-Fi + NTP + MQTT (QoS 1) com maquina de estados e reconexao.
// Biblioteca MQTT: "MQTT" de Joel Gaehwiler (256dpi/lwmqtt). A PubSubClient, mais
// comum em tutorial, NAO serve: so publica em QoS 0 e o TC1 exige QoS 1 (UC05).
#ifndef REDE_H
#define REDE_H

#include <WiFi.h>
#include <MQTT.h>
#include <time.h>
#include "config.h"

enum EstadoRede {
  REDE_WIFI_CONECTANDO,
  REDE_NTP_SYNC,
  REDE_MQTT_CONECTANDO,
  REDE_ONLINE,
  REDE_OFFLINE
};

// Epoch acima disto (jun/2025) significa que o SNTP ja sincronizou. Antes do
// primeiro sync o RTC interno conta desde 1/1/1970 e o ts nao serve para nada.
const time_t EPOCH_MINIMO_VALIDO = 1750000000;

// Wi-Fi: intervalo fixo entre tentativas (o driver do ESP32 ja tenta por dentro).
const unsigned long REDE_INTERVALO_WIFI_MS = 10000UL;

// MQTT: backoff exponencial (spec, secao 6.1) para nao martelar um broker fora do
// ar. Zera quando o Wi-Fi (re)conecta, para que a volta da rede seja seguida de
// uma tentativa imediata em vez de esperar o backoff acumulado (importa no CT03).
const unsigned long REDE_BACKOFF_MQTT_MIN_MS = 5000UL;
const unsigned long REDE_BACKOFF_MQTT_MAX_MS = 30000UL;

// keepAlive de 15 s detecta a queda do broker em ~22 s. O timeout e o tempo que a
// lib espera pelo CONNACK e pelo PUBACK do QoS 1: o default de 1 s da falso
// negativo em Wi-Fi domestico, e mesmo 3 s ainda deu erro=-9
// (MISSING_OR_WRONG_PACKET) numa publicacao que o broker recebeu -- o PUBACK
// chegou tarde, a lib fechou a conexao e a leitura entraria de novo no buffer,
// virando duplicata. 5 s cobre a latencia da internet; o preco e o laco ficar
// bloqueado por ate 5 s quando a publicacao realmente falha.
const int REDE_KEEPALIVE_S = 15;
const int REDE_TIMEOUT_MS  = 5000;

static WiFiClient redeWifiClient;
static MQTTClient redeMqtt(256);  // payload das leituras fica em ~110 bytes

static EstadoRede redeEstadoAtual = REDE_WIFI_CONECTANDO;
static unsigned long redeUltimaTentativaWifi = 0;
static unsigned long redeUltimaTentativaMqtt = 0;
static unsigned long redeBackoffMqttMs = REDE_BACKOFF_MQTT_MIN_MS;
static bool redeMqttTentarAgora = true;
static bool redeNtpOk = false;
static bool redeWifiEstavaConectado = false;
// Depois da primeira vez online, cair de conexao e OFFLINE (buffer + bip), nao
// mais "conectando" — a UI e o CT03 dependem dessa distincao.
static bool redeJaEsteveOnline = false;

// Topico de comando do aerador, assinado a cada conexao: com sessao limpa o broker
// esquece a assinatura quando o no cai. Vazio = nao assina nada.
static String redeTopicoComando;

// ---- Gatilho de teste do CT03 ----
// Derrubar o roteador nao serve de teste nesta bancada: a internet do PC vem por
// cabo do Mac que a compartilha, entao o roteador cair tira o broker do ar junto e
// o cenario deixaria de ser "no offline, broker de pe". Este gatilho corta so o
// radio do no, por tempo determinado, e suspende a reconexao automatica enquanto
// dura -- reproduzivel e sem mexer na infraestrutura.
static unsigned long redeTesteOfflineFimMs = 0;
static bool redeTesteOfflineAtivo = false;

inline String macLimpo() {
  String mac = WiFi.macAddress();  // "A0:B1:C2:D3:E4:F5"
  mac.replace(":", "");
  mac.toLowerCase();
  return mac;
}

inline EstadoRede redeEstado() { return redeEstadoAtual; }
inline bool redeOnline() { return redeEstadoAtual == REDE_ONLINE; }
inline bool relogioValido() { return time(nullptr) > EPOCH_MINIMO_VALIDO; }

inline void redeIniciar() {
  WiFi.mode(WIFI_STA);
  // Sem isso o modem-sleep adia pacotes por dezenas de ms e o PUBACK do QoS 1
  // chega depois do timeout, o que faz a lib fechar uma conexao que estava boa.
  WiFi.setSleep(false);
  // Explicito porque o gatilho de teste do CT03 desliga isso por alguns segundos.
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  configTime(0, 0, "a.st1.ntp.br", "pool.ntp.org");  // UTC; fuso e problema do backend
  redeMqtt.begin(MQTT_BROKER_IP, MQTT_BROKER_PORTA, redeWifiClient);
  redeMqtt.setOptions(REDE_KEEPALIVE_S, true, REDE_TIMEOUT_MS);
  redeEstadoAtual = REDE_WIFI_CONECTANDO;
  redeUltimaTentativaWifi = millis();
  Serial.printf("Rede: SSID \"%s\", broker %s:%d\n", WIFI_SSID, MQTT_BROKER_IP, MQTT_BROKER_PORTA);
}

// Registra o topico de comando e quem trata a mensagem. Chamar uma vez no setup,
// depois do redeIniciar() (o topico usa o MAC). A biblioteca chama `aoReceber` de
// dentro do redeMqtt.loop(): nao publicar nem assinar dentro dele.
inline void redeAssinarComandos(const String& topico, MQTTClientCallbackSimple aoReceber) {
  redeTopicoComando = topico;
  redeMqtt.onMessage(aoReceber);
}

// Corta o Wi-Fi por `duracaoMs` para executar o CT03. Acionado pelo comando
// "queda" no Serial (ver no_sensor.ino); nao entra no caminho normal do firmware.
inline void redeSimularQueda(unsigned long duracaoMs) {
  Serial.printf("TESTE: derrubando o Wi-Fi por %lu ms (CT03)\n", duracaoMs);
  redeMqtt.disconnect();           // DISCONNECT limpo enquanto o radio ainda esta de pe
  WiFi.setAutoReconnect(false);    // senao o driver religa por dentro em poucos segundos
  WiFi.disconnect();
  redeWifiEstavaConectado = false;  // para a volta ser logada com ip/rssi, como uma queda real
  redeTesteOfflineFimMs = millis() + duracaoMs;
  redeTesteOfflineAtivo = true;
}

inline bool redeEmTesteOffline() { return redeTesteOfflineAtivo; }

inline void redeLoop() {
  unsigned long agora = millis();

  // ---- Janela de teste do CT03: fica offline de proposito ----
  // A subtracao com cast para long e o teste de "ja passou?" que sobrevive ao
  // estouro do millis() em 49 dias; comparar `agora >= fim` direto nao sobrevive.
  if (redeTesteOfflineAtivo) {
    if ((long)(agora - redeTesteOfflineFimMs) < 0) {
      redeEstadoAtual = redeJaEsteveOnline ? REDE_OFFLINE : REDE_WIFI_CONECTANDO;
      return;
    }
    redeTesteOfflineAtivo = false;
    Serial.println("TESTE: fim da janela offline, religando o Wi-Fi");
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_SENHA);
    redeUltimaTentativaWifi = agora;
    redeBackoffMqttMs = REDE_BACKOFF_MQTT_MIN_MS;
    redeMqttTentarAgora = true;
    return;
  }

  redeMqtt.loop();  // keepAlive e recebimento; retorna na hora se desconectado

  // ---- Wi-Fi ----
  if (WiFi.status() != WL_CONNECTED) {
    if (redeWifiEstavaConectado) {
      redeWifiEstavaConectado = false;
      Serial.println("Rede: Wi-Fi caiu");
    }
    redeEstadoAtual = redeJaEsteveOnline ? REDE_OFFLINE : REDE_WIFI_CONECTANDO;
    if (agora - redeUltimaTentativaWifi >= REDE_INTERVALO_WIFI_MS) {
      redeUltimaTentativaWifi = agora;
      Serial.printf("Rede: sem Wi-Fi (status=%d), tentando de novo\n", (int)WiFi.status());
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_SENHA);
    }
    return;
  }

  if (!redeWifiEstavaConectado) {
    redeWifiEstavaConectado = true;
    redeBackoffMqttMs = REDE_BACKOFF_MQTT_MIN_MS;
    redeMqttTentarAgora = true;
    Serial.printf("Rede: Wi-Fi OK ip=%s rssi=%d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
  }

  // ---- Relogio (pre-condicao para publicar: ts invalido contamina o banco) ----
  if (!redeNtpOk) {
    redeEstadoAtual = REDE_NTP_SYNC;
    redeNtpOk = relogioValido();
    if (!redeNtpOk) return;
    Serial.printf("Rede: relogio sincronizado (epoch=%lu)\n", (unsigned long)time(nullptr));
  }

  // ---- MQTT ----
  if (!redeMqtt.connected()) {
    redeEstadoAtual = redeJaEsteveOnline ? REDE_OFFLINE : REDE_MQTT_CONECTANDO;
    if (redeMqttTentarAgora || agora - redeUltimaTentativaMqtt >= redeBackoffMqttMs) {
      redeUltimaTentativaMqtt = agora;
      redeMqttTentarAgora = false;
      String clientId = "no-sensor-" + macLimpo();
      if (!redeMqtt.connect(clientId.c_str())) {
        redeBackoffMqttMs *= 2;
        if (redeBackoffMqttMs > REDE_BACKOFF_MQTT_MAX_MS) redeBackoffMqttMs = REDE_BACKOFF_MQTT_MAX_MS;
        Serial.printf("Rede: MQTT nao conectou (erro=%d rc=%d), proxima em %lu ms\n",
                      (int)redeMqtt.lastError(), (int)redeMqtt.returnCode(), redeBackoffMqttMs);
      } else if (redeTopicoComando.length() > 0 && !redeMqtt.subscribe(redeTopicoComando.c_str(), 1)) {
        // Sem a assinatura o comando do aerador nao chega: fecha e tenta de novo
        // na proxima janela de reconexao, em vez de ficar online "surdo".
        Serial.printf("Rede: falha ao assinar %s (erro=%d), reconectando\n",
                      redeTopicoComando.c_str(), (int)redeMqtt.lastError());
        redeMqtt.disconnect();
      }
    }
    return;
  }

  if (redeEstadoAtual != REDE_ONLINE) Serial.println("Rede: MQTT conectado (online)");
  redeEstadoAtual = REDE_ONLINE;
  redeJaEsteveOnline = true;
  redeBackoffMqttMs = REDE_BACKOFF_MQTT_MIN_MS;
}

// Publica em QoS 1. false = nada confirmado pelo broker: a leitura tem que
// continuar no buffer (a lib fecha a conexao quando o PUBACK nao vem, e o laco
// reconecta na proxima passada).
inline bool redePublicar(const char* topico, const char* payload) {
  if (!redeMqtt.connected()) return false;
  if (redeMqtt.publish(topico, payload, false, 1)) return true;  // retain=false, QoS 1

  // Falha de publish deixa a conexao suspeita, e derrubar o socket aqui NAO e
  // zelo excessivo: parte dos erros da lwmqtt (LWMQTT_NETWORK_FAILED_WRITE, por
  // exemplo) nao fecham a conexao por dentro. Sem este disconnect, connected()
  // seguia true, o redeLoop() remarcava ONLINE, e o dreno tentava de novo na
  // passada seguinte -- a cada ~10 ms, sem limite. Em 23/08 isso encheu a serial
  // com 5955 linhas truncadas da mesma leitura e derrubou a placa em ciclo de
  // brownout (27 resets), porque a martelada no radio afundou o 3V3 do USB.
  // Fechando aqui, a reconexao passa pelo backoff exponencial que ja existe.
  Serial.printf("Rede: publish falhou (erro=%d), fechando a conexao para reconectar com backoff\n",
                (int)redeMqtt.lastError());
  redeMqtt.disconnect();
  redeEstadoAtual = redeJaEsteveOnline ? REDE_OFFLINE : REDE_MQTT_CONECTANDO;
  redeUltimaTentativaMqtt = millis();
  redeMqttTentarAgora = false;
  return false;
}

#endif
