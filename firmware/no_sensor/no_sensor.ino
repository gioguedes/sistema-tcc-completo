// Firmware do no sensor - TCC piscicultura. v3: v2 (buffer offline + ressincronizacao,
// CT03) + comando do aerador pelo painel (MQTT).
// Arquitetura: TODA leitura entra no buffer e o laco drena publicando a mais antiga
// quando online. Fluxo normal e ressincronizacao passam pelo mesmo caminho -- o
// fluxo normal e so o caso em que a fila tem um item. Isso evita a duplicacao de
// codigo (e de bugs) entre "publicar agora" e "publicar o represado".
#include <ArduinoJson.h>
#include "config.h"
#include "sensores.h"
#include "buffer_leituras.h"
#include "display_ui.h"
#include "rede.h"

unsigned long ultimaLeituraMs = 0;
Leitura ultimaLeitura;
bool temLeitura = false;
uint8_t errosAnteriores = 0;
EstadoRede estadoAnterior = REDE_WIFI_CONECTANDO;
String topicoLeituras;
String topicoAerador;

// Bitmask dos sensores em falha, para bipar so na transicao (a spec pede 2 bips
// no erro de sensor; sem isso o buzzer tocaria a cada ciclo enquanto durasse).
uint8_t mascaraErros(const Leitura& l) {
  uint8_t m = 0;
  if (isnan(l.ph))          m |= 0x01;
  if (isnan(l.temperatura)) m |= 0x02;
  if (isnan(l.turbidez))    m |= 0x04;
  return m;
}

// Duas casas decimais. Sem isso o ArduinoJson serializa o float inteiro
// ("ph":5.09817) e publica precisao que o sensor nao tem: o ADC resolve ~1 mV,
// o que da ~0,005 de pH. A spec (secao 6.2) tambem mostra o payload assim.
inline float arredondar2(float v) { return roundf(v * 100.0f) / 100.0f; }

// Formato consumido pelo backend no sub-projeto 2 (spec, secao 6.2). Sensor em
// falha vira null, nao zero - zero seria dado plausivel e mentiroso.
void montarPayload(const Leitura& l, char* buf, size_t n) {
  JsonDocument doc;
  doc["mac"] = macLimpo();
  doc["ts"]  = (uint32_t)l.ts;
  if (isnan(l.ph))          doc["ph"]          = nullptr; else doc["ph"]          = arredondar2(l.ph);
  if (isnan(l.temperatura)) doc["temperatura"] = nullptr; else doc["temperatura"] = arredondar2(l.temperatura);
  if (isnan(l.turbidez))    doc["turbidez"]    = nullptr; else doc["turbidez"]    = arredondar2(l.turbidez);
  serializeJson(doc, buf, n);
}

const char* nomeEstado(EstadoRede e) {
  switch (e) {
    case REDE_WIFI_CONECTANDO: return "Conectando Wi-Fi...";
    case REDE_NTP_SYNC:        return "Sincronizando hora";
    case REDE_MQTT_CONECTANDO: return "Conectando MQTT...";
    case REDE_ONLINE:          return "MQTT OK";
    case REDE_OFFLINE:         return "OFFLINE";
  }
  return "?";
}

// Comando do aerador vindo do painel: API -> broker -> no (sub-projeto 5, F-02 do Figma).
// Payload {"acao":"ligar"|"desligar","id":N,"ts":epoch}. A API publica com retain: ao
// (re)conectar, o no recebe o ultimo comando e volta ao estado pedido. No boot o rele
// continua DESLIGADO (setup) ate essa mensagem chegar.
void aoReceberComandoAerador(String &topico, String &payload) {
  if (topico != topicoAerador) return;
  JsonDocument doc;
  if (deserializeJson(doc, payload)) {
    // payload vazio = retido apagado no broker; qualquer outro e mensagem malformada
    if (payload.length() > 0) Serial.println("Aerador: comando ignorado (JSON invalido): " + payload);
    return;
  }
  const char* acao = doc["acao"] | "";
  bool ligar;
  if (strcmp(acao, "ligar") == 0) {
    ligar = true;
  } else if (strcmp(acao, "desligar") == 0) {
    ligar = false;
  } else {
    Serial.println("Aerador: comando ignorado (acao desconhecida): " + payload);
    return;
  }
  digitalWrite(PIN_RELE, ligar ? RELE_LIGADO : RELE_DESLIGADO);
  Serial.printf("Aerador %s (comando %ld do painel)\n", ligar ? "LIGADO" : "DESLIGADO", (long)(doc["id"] | 0));
}

// Comandos de bancada. Existem por causa do CT03: nesta rede derrubar o roteador
// tira o broker do ar junto com o no (ver rede.h), e a queda precisa ser
// reproduzivel para virar evidencia.
void tratarComandoSerial() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd == "queda") {
    redeSimularQueda(TESTE_QUEDA_REDE_MS);
  } else if (cmd == "ler") {
    // Antecipa o proximo ciclo em vez de ler aqui dentro: a leitura continua
    // acontecendo no unico lugar do laco que a faz, entao nao ha caminho
    // paralelo para o buffer. Existe para os criterios de aceite 2 e 4 seguirem
    // executaveis com o intervalo de entrega (60 s) gravado na placa.
    ultimaLeituraMs = 0;
    Serial.println("Leitura antecipada para o proximo ciclo do laco.");
  } else if (cmd == "buffer") {
    Serial.printf("Buffer: %d/%d na fila, pico de %d, %lu descartada(s)\n",
                  bufferTamanho(), BUFFER_CAPACIDADE, bufferPico(),
                  (unsigned long)bufferDescartadas());
  } else {
    Serial.printf("Comando \"%s\" desconhecido. Use: queda | ler | buffer\n", cmd.c_str());
  }
}

void setup() {
  Serial.begin(115200);
  // Limita o bloqueio do readStringUntil quando chega texto sem \n (o default e 1 s).
  Serial.setTimeout(50);

  // Rele ATIVO-BAIXO (Task 3): tem que nascer em HIGH, senao a bomba liga no boot.
  pinMode(PIN_RELE, OUTPUT);
  digitalWrite(PIN_RELE, RELE_DESLIGADO);

  uiIniciar();
  sensoresIniciar();
  uiChecarLed();

  Serial.println();
  Serial.println("no_sensor v3 - leitura integrada + MQTT QoS 1 + buffer offline + aerador");
#if !PH_CALIBRADO
  Serial.println("AVISO: pH usa constantes de fabrica (nao calibrado). O valor de pH");
  Serial.println("       serve para conferir a resposta do sensor, nao como medida.");
#endif
  Serial.printf("Intervalo de leitura: %lu ms | buffer: %d leituras\n",
                INTERVALO_LEITURA_MS, BUFFER_CAPACIDADE);
  Serial.println("Comandos no Serial: queda | ler | buffer");

  ultimaLeitura = leituraVazia();
  redeIniciar();
  topicoLeituras = String(MQTT_TOPICO_PREFIXO) + "/" + macLimpo() + "/leituras";
  Serial.println("Topico: " + topicoLeituras);
  topicoAerador = String(MQTT_TOPICO_PREFIXO) + "/" + macLimpo() + "/aerador";
  redeAssinarComandos(topicoAerador, aoReceberComandoAerador);
  Serial.println("Topico de comando: " + topicoAerador);
}

void loop() {
  tratarComandoSerial();
  redeLoop();
  EstadoRede estado = redeEstado();

  // Bip curto na transicao online -> offline (spec, secao 6.5).
  if (estado == REDE_OFFLINE && estadoAnterior == REDE_ONLINE) uiBipCurto();
  estadoAnterior = estado;

  // O ciclo de leitura so comeca com o relogio sincronizado: sem isso o ts sai
  // como segundos desde o boot e o backend recebe leitura datada de 1970. Depois
  // do primeiro sync o RTC interno mantem a hora offline, que e o que permite
  // bufferizar com timestamp verdadeiro.
  if (relogioValido() &&
      (ultimaLeituraMs == 0 || millis() - ultimaLeituraMs >= INTERVALO_LEITURA_MS)) {
    ultimaLeituraMs = millis();
    ultimaLeitura = sensoresLer();
    temLeitura = true;

    uint8_t erros = mascaraErros(ultimaLeitura);
    if (erros & ~errosAnteriores) uiBipDuplo();  // surgiu falha nova
    errosAnteriores = erros;

    bool estavaCheio = bufferCheio();
    bufferGuardar(ultimaLeitura);
    Serial.printf("Leitura na fila (buffer=%d): ph=%.2f temp=%.1f turb=%.1f\n",
                  bufferTamanho(), ultimaLeitura.ph, ultimaLeitura.temperatura,
                  ultimaLeitura.turbidez);
    if (estavaCheio) {
      Serial.printf("AVISO: buffer cheio, descartada a leitura mais antiga (%lu no total)\n",
                    (unsigned long)bufferDescartadas());
    }
  }

  // Drenagem: uma publicacao por passada do laco. Drenar a fila inteira de uma vez
  // seguraria o redeLoop() (keepAlive) e a UI durante a rajada de ressincronizacao.
  if (redeOnline() && !bufferVazio()) {
    Leitura pendente = bufferProxima();
    char payload[192];
    montarPayload(pendente, payload, sizeof(payload));
    if (redePublicar(topicoLeituras.c_str(), payload)) {
      bufferRemover();
      Serial.printf("Publicado (%d na fila): %s\n", bufferTamanho(), payload);
    } else {
      // Continua na fila e volta na proxima passada. Se o PUBACK se perdeu na
      // volta, o broker pode ja ter recebido: a republicacao e duplicata legitima
      // do QoS 1 (at-least-once). O backend do sub-projeto 2 deduplica por (mac, ts).
      Serial.printf("FALHA ao publicar (%d na fila): %s\n", bufferTamanho(), payload);
    }
  }

  uiLed(estado == REDE_ONLINE     ? LED_FIXO :
        estado == REDE_OFFLINE    ? LED_PISCA_RAPIDO :
                                    LED_PISCA_LENTO);

  // uiMostrar ja limita o redesenho a 500 ms por dentro.
  uiMostrar(nomeEstado(estado), ultimaLeitura, bufferTamanho(), temLeitura);
  delay(10);
}
