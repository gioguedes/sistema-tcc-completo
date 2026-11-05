// DIAGNOSTICO 1-WIRE — em que etapa o DS18B20 falha?
// ---------------------------------------------------------------------------
// Quando o sensor "nao aparece", a causa pode estar em quatro pontos muito
// diferentes, e o teste de presenca comum nao os separa. Este sketch percorre
// as etapas na ordem e diz em qual delas parou:
//
//   1) pulso de presenca   -> prova que DADOS e GND chegam ao sensor
//   2) comando 0xB4        -> o proprio sensor informa se o VDD chegou nele
//   3) search()            -> le o ROM de 64 bits (exige comunicacao estavel)
//   4) 0x44 + 0xBE         -> converte e le a temperatura do scratchpad
//
// Serial Monitor a 115200 baud. Nao precisa de ninguem olhando a bancada.
//
// LICAO REGISTRADA (2026-08-24): a primeira versao deste sketch tentava achar
// o sensor pelo tempo de subida da linha, apostando que o capacitor interno de
// ~800 pF a deixaria lenta. NAO FUNCIONA: esse capacitor fica atras de um diodo
// que so conduz com a linha alta, entao ele nao e descarregado pelo pulso e nao
// atrasa a subida. Medido na bancada: linha com sensor subiu em 508 ns, igual a
// linha vazia. A varredura de subida continua aqui, mas so serve para achar
// pino preso ao terra — nao para detectar 1-Wire.
#include <OneWire.h>
#include "soc/gpio_struct.h"
#include "soc/gpio_reg.h"

const uint8_t PINO_DADOS = 25;   // conferido pela varredura cega de 24/08

const uint8_t PINOS[] = {13, 12, 14, 27, 26, 25, 33, 32, 2, 4, 5, 15, 16, 17, 18, 19, 21, 22, 23};
const int8_t  LINHA[] = { 5,  7,  8,  9, 10, 11, 12, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
const int N = sizeof(PINOS) / sizeof(PINOS[0]);

// --- acesso direto aos registradores de GPIO -------------------------------
// pinMode() leva microssegundos e mascararia o que queremos medir.
static inline void saidaLiga(uint8_t g) {
  if (g < 32) GPIO.enable_w1ts      = (1UL << g);
  else        GPIO.enable1_w1ts.val = (1UL << (g - 32));
}
static inline void saidaSolta(uint8_t g) {
  if (g < 32) GPIO.enable_w1tc      = (1UL << g);
  else        GPIO.enable1_w1tc.val = (1UL << (g - 32));
}
static inline void nivelBaixo(uint8_t g) {
  if (g < 32) GPIO.out_w1tc      = (1UL << g);
  else        GPIO.out1_w1tc.val = (1UL << (g - 32));
}
static inline int leNivel(uint8_t g) {
  if (g < 32) return (GPIO.in  >> g) & 1;
  else        return (GPIO.in1.val >> (g - 32)) & 1;
}

void titulo(const char* t) {
  Serial.println();
  Serial.println("======================================================================");
  Serial.print("  "); Serial.println(t);
  Serial.println("======================================================================");
}

uint32_t tempoDeSubidaNs(uint8_t g) {
  pinMode(g, INPUT_PULLUP);
  delay(2);
  if (leNivel(g) == 0) return 0;

  nivelBaixo(g);
  saidaLiga(g);
  delayMicroseconds(800);

  const uint32_t mhz  = getCpuFrequencyMhz();
  const uint32_t teto = mhz * 2000;

  noInterrupts();
  uint32_t t0 = ESP.getCycleCount();
  saidaSolta(g);
  uint32_t dt = 0;
  while (leNivel(g) == 0) {
    dt = ESP.getCycleCount() - t0;
    if (dt > teto) break;
  }
  uint32_t t1 = ESP.getCycleCount();
  interrupts();

  pinMode(g, INPUT);
  uint32_t ciclos = t1 - t0;
  if (ciclos > teto) return 0;
  return (uint32_t)(((uint64_t)ciclos * 1000ULL) / mhz);
}

void varrerSubida() {
  titulo("0) TEMPO DE SUBIDA (so localiza pino presd ao terra — ver licao no topo)");
  for (int i = 0; i < N; i++) {
    uint32_t t = tempoDeSubidaNs(PINOS[i]);
    Serial.print("  GPIO"); Serial.print(PINOS[i]);
    if (LINHA[i] > 0) { Serial.print(" / linha "); Serial.print(LINHA[i]); }
    else                Serial.print(" / 2a fileira");
    Serial.print("  ->  ");
    if (t == 0) Serial.println("preso em nivel baixo (carga ate o terra)");
    else      { Serial.print(t); Serial.println(" ns"); }
  }
}

// Reset feito na mao, com o desenho do que aconteceu depois. Prova DADOS+GND.
void resetComDesenho(uint8_t g) {
  titulo("1) PULSO DE PRESENCA (prova que DADOS e GND chegam ao sensor)");

  const int AMOSTRAS = 90;
  uint8_t bits[AMOSTRAS];

  pinMode(g, INPUT_PULLUP);
  delay(2);
  nivelBaixo(g);
  saidaLiga(g);
  delayMicroseconds(500);

  noInterrupts();
  saidaSolta(g);
  for (int i = 0; i < AMOSTRAS; i++) {
    bits[i] = leNivel(g);
    delayMicroseconds(2);
  }
  interrupts();
  pinMode(g, INPUT);

  Serial.print("  linha apos soltar (cada caractere ~2 us):\n  ");
  for (int i = 0; i < AMOSTRAS; i++) Serial.print(bits[i] ? '-' : '_');
  Serial.println();

  int puxadas = 0, maiorSeq = 0, seq = 0, inicio = -1;
  for (int i = 1; i < AMOSTRAS; i++) {
    if (!bits[i]) {
      if (seq == 0 && inicio < 0) inicio = i;
      seq++; puxadas++;
      if (seq > maiorSeq) maiorSeq = seq;
    } else seq = 0;
  }
  if (puxadas == 0) {
    Serial.println("  -> ninguem puxou a linha: DADOS ou GND nao chegam ao sensor.");
  } else {
    Serial.print("  -> PRESENCA: inicio ~"); Serial.print(inicio * 2);
    Serial.print(" us, duracao ~"); Serial.print(maiorSeq * 2); Serial.println(" us.");
    Serial.println("     (norma: inicio 15-60 us, duracao 60-240 us)");
  }
}

// As tres etapas seguintes usam a biblioteca, que e o que o firmware do no usa.
void etapasDaLib(uint8_t g) {
  OneWire ow(g);

  // --- 2) alimentacao, perguntada ao proprio sensor ------------------------
  titulo("2) ALIMENTACAO — comando 0xB4 (READ POWER SUPPLY)");
  Serial.println("  Por SKIP ROM, entao funciona mesmo sem conhecer o endereco.");
  Serial.println("  Resposta 1 = VDD externo presente. Resposta 0 = modo parasita,");
  Serial.println("  ou seja, o fio VERMELHO nao esta levando 3,3 V ao sensor.");
  Serial.println();

  if (!ow.reset()) {
    Serial.println("  reset() da biblioteca NAO viu presenca — para aqui.");
    Serial.println("  (se a etapa 1 viu presenca e esta nao ve, o problema e de");
    Serial.println("   timing/ruido na linha, nao de fiacao)");
    return;
  }
  Serial.println("  reset() da biblioteca: presenca OK");

  ow.reset();
  ow.skip();
  ow.write(0xB4);
  int alimentado = ow.read_bit();
  Serial.print("  resposta ao 0xB4: "); Serial.print(alimentado);
  Serial.println(alimentado ? "  <- VDD PRESENTE (fio vermelho chegando)"
                            : "  <- MODO PARASITA: o VDD NAO chega ao sensor");

  // --- 3) ROM --------------------------------------------------------------
  titulo("3) LEITURA DO ROM (search)");
  uint8_t rom[8];
  int achados = 0;
  ow.reset_search();
  while (ow.search(rom)) {
    Serial.print("  ROM: ");
    for (int i = 0; i < 8; i++) {
      if (rom[i] < 16) Serial.print('0');
      Serial.print(rom[i], HEX);
    }
    bool crcOk = (OneWire::crc8(rom, 7) == rom[7]);
    Serial.print(crcOk ? "   CRC ok" : "   CRC FALHOU <- ruido ou alimentacao instavel");
    if (rom[0] == 0x28) Serial.print("   familia 0x28 = DS18B20");
    Serial.println();
    achados++;
  }
  if (achados == 0) {
    Serial.println("  search() nao devolveu nenhum ROM.");
    Serial.println("  Presenca sem ROM = o sensor responde ao reset mas nao consegue");
    Serial.println("  sustentar a conversa. Causa tipica: VDD ausente ou instavel.");
  }

  // --- 4) temperatura ------------------------------------------------------
  titulo("4) CONVERSAO E LEITURA DA TEMPERATURA (0x44 + 0xBE)");
  if (!ow.reset()) { Serial.println("  sem presenca no reset — nao da para converter."); return; }
  ow.skip();
  ow.write(0x44, 1);          // converte, com pull-up forte ligado
  delay(900);

  if (!ow.reset()) { Serial.println("  sem presenca apos a conversao."); return; }
  ow.skip();
  ow.write(0xBE);             // le o scratchpad
  uint8_t sp[9];
  for (int i = 0; i < 9; i++) sp[i] = ow.read();

  Serial.print("  scratchpad: ");
  for (int i = 0; i < 9; i++) {
    if (sp[i] < 16) Serial.print('0');
    Serial.print(sp[i], HEX); Serial.print(' ');
  }
  Serial.println();

  bool crcOk = (OneWire::crc8(sp, 8) == sp[8]);
  Serial.print("  CRC do scratchpad: "); Serial.println(crcOk ? "ok" : "FALHOU");

  bool tudoUm = true, tudoZero = true;
  for (int i = 0; i < 9; i++) { if (sp[i] != 0xFF) tudoUm = false; if (sp[i] != 0x00) tudoZero = false; }
  if (tudoUm)   Serial.println("  scratchpad todo FF = a linha ficou solta o tempo todo.");
  if (tudoZero) Serial.println("  scratchpad todo 00 = a linha ficou presa em baixo.");

  int16_t bruto = (int16_t)((sp[1] << 8) | sp[0]);
  float temp = bruto / 16.0f;
  Serial.print("  temperatura: "); Serial.print(temp); Serial.println(" C");
  if (temp >= 84.9f && temp <= 85.1f)
    Serial.println("  85.00 = valor de fabrica: o sensor NAO converteu (falta energia).");
}

void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println();
  Serial.println("### DIAGNOSTICO 1-WIRE — em que etapa o DS18B20 falha? ###");
  Serial.print("### CPU a "); Serial.print(getCpuFrequencyMhz()); Serial.println(" MHz ###");

  varrerSubida();
  resetComDesenho(PINO_DADOS);
  etapasDaLib(PINO_DADOS);

  Serial.println();
  Serial.println("### FIM ###");
}

void loop() {
  delay(10000);
}
