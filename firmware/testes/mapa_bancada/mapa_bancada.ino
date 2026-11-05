// MAPA CEGO DA BANCADA
// ---------------------------------------------------------------------------
// Descobre o que esta ligado em cada pino do ESP32 SEM assumir nada sobre a
// fiacao. Nenhuma constante de projeto aqui: tudo que este sketch imprime foi
// medido na hora. Serve para reconstruir o mapa da bancada depois de mexer nos
// jumpers, ou para conferir se o mapa documentado ainda bate com a realidade.
//
// Serial Monitor a 115200 baud.
//
// Fases 1 a 5 rodam sozinhas no boot (~40 s) e nao precisam de ninguem olhando.
// A fase 6 (loop) aciona uma saida por vez, numerada, para localizar LED,
// buzzer e rele pelo que se ve e se ouve - a unica parte que precisa de olho.
//
// SEGURANCA
//   - no maximo UM pino em OUTPUT por vez (nunca ha dois drivers brigando);
//   - GPIO 6..11 (flash), 0 (boot) e 1/3 (Serial) nunca sao tocados;
//   - pino amarrado direto ao 3V3 ou ao terra nao e dirigido como saida;
//   - carga de baixa resistencia (bobina de buzzer) recebe so o tom, nunca
//     nivel continuo, para nao passar do limite de 40 mA por pino.
//
// TRES ERROS DESTE SKETCH, CORRIGIDOS EM 2026-08-24 APOS MEDICAO NA BANCADA:
//
//  (a) ORDEM DAS VARREDURAS. A varredura I2C rodava antes da 1-Wire e testava
//      dezenas de pares de pinos. No ESP32, pinMode() NAO desfaz o roteamento
//      da matriz de periodicos: o driver do I2C continuava presente no pino,
//      a linha ficava presa, e o OneWire::reset() falhava. Resultado: o
//      DS18B20 apareceu como "nao existe" tres vezes seguidas, estando
//      perfeito. Agora o 1-Wire vem PRIMEIRO e todo pino usado pelo Wire leva
//      gpio_reset_pin() ao sair.
//
//  (b) TENSAO COM PULL-UP INTERNO NAO SIGNIFICA NADA. O ADC do ESP32 carrega
//      o pino quando a fonte tem impedancia alta, e o pull-up interno tem
//      ~45 kOhm. Medido: pinos comprovadamente vazios leram de 1625 a 2818 mV,
//      espalhados. A heuristica "1500-2200 mV = LED em serie" dava falso
//      positivo em quase tudo. O veredito agora sai do NIVEL LOGICO; a tensao
//      fica impressa apenas como dado bruto, com aviso.
//
//  (c) BOBINA NAO E CURTO. O buzzer magnetico tem ~30 Ohm em corrente
//      continua e era classificado como "amarrado no terra", o que fazia o
//      sketch se recusar a aciona-lo. Agora, quando o pino parece aterrado,
//      um pulso curto mede a tensao que ele sustenta sob carga: o driver do
//      ESP32 tem ~40 Ohm de saida, entao curto real colapsa para perto de
//      zero e bobina de 30 Ohm segura ~1,4 V.
#include <Wire.h>
#include <OneWire.h>
#include "driver/gpio.h"

// ---------------------------------------------------------------------------
// Tabela de pinos. 'linha' e a linha da protoboard onde aquele pino da placa
// cai, valendo para a fileira em que a DevKitC de 38 pinos esta espetada
// (linha 1 = 5V ... linha 19 = 3V3). -1 = pino da fileira oposta, que nesta
// bancada nao esta na protoboard.
struct PinoInfo {
  uint8_t gpio;
  bool    saida;  // pode virar OUTPUT (34..39 sao somente entrada)
  bool    adc;    // tem ADC - sem Wi-Fi ligado, o ADC2 tambem funciona
  int8_t  linha;
};

const PinoInfo PINOS[] = {
  {13, true,  true,   5}, {12, true,  true,   7}, {14, true,  true,   8},
  {27, true,  true,   9}, {26, true,  true,  10}, {25, true,  true,  11},
  {33, true,  true,  12}, {32, true,  true,  13}, {35, false, true,  14},
  {34, false, true,  15}, {39, false, true,  16}, {36, false, true,  17},
  { 2, true,  true,  -1}, { 4, true,  true,  -1}, { 5, true,  false, -1},
  {15, true,  true,  -1}, {16, true,  false, -1}, {17, true,  false, -1},
  {18, true,  false, -1}, {19, true,  false, -1}, {21, true,  false, -1},
  {22, true,  false, -1}, {23, true,  false, -1},
};
const int N = sizeof(PINOS) / sizeof(PINOS[0]);

struct Perfil {
  int  mvUp   = -1;      // tensao com pull-up interno - DADO BRUTO, ver erro (b)
  int  mvDn   = -1;      // tensao com pull-down interno - idem
  int  nUp    = -1;      // nivel logico com pull-up   <- confiavel
  int  nDn    = -1;      // nivel logico com pull-down <- confiavel
  int  mvCarga = -1;     // tensao sustentada sob pulso de saida
  bool seguro = true;    // pode ser dirigido com nivel continuo
  bool cargaBaixa = false; // conduz ate o terra, mas nao e curto (bobina)
  const char* veredito = "?";
};
Perfil perfis[N];

bool conectado[N][N];
int  i2cSda = -1, i2cScl = -1;   // indices dos pinos do barramento, se achado

// ---------------------------------------------------------------------------
void titulo(const char* t) {
  Serial.println();
  Serial.println("======================================================================");
  Serial.print("  "); Serial.println(t);
  Serial.println("======================================================================");
}

void ondeFica(int i, char* buf, size_t n) {
  if (PINOS[i].linha > 0)
    snprintf(buf, n, "GPIO%-2d/linha %-2d", PINOS[i].gpio, PINOS[i].linha);
  else
    snprintf(buf, n, "GPIO%-2d/2a fileira", PINOS[i].gpio);
}

int mediaMv(uint8_t gpio, int amostras) {
  uint32_t soma = 0;
  for (int i = 0; i < amostras; i++) {
    soma += analogReadMilliVolts(gpio);
    delayMicroseconds(150);
  }
  return (int)(soma / amostras);
}

// Mede a tensao que o pino sustenta dirigindo alto contra a carga. Ver erro (c).
// Pulso curto: mesmo num curto franco a corrente dura microssegundos.
int tensaoSobCarga(uint8_t gpio) {
  pinMode(gpio, OUTPUT);
  digitalWrite(gpio, HIGH);
  delayMicroseconds(60);
  int mv = analogReadMilliVolts(gpio);
  digitalWrite(gpio, LOW);
  pinMode(gpio, INPUT);
  return mv;
}

// ---------------------------------------------------------------------------
// FASE 1 - assinatura de cada pino, pelo NIVEL LOGICO (ver erro (b)).
void fase1_assinatura() {
  titulo("FASE 1 - ASSINATURA DE CADA PINO");
  Serial.println("  Veredito vem do nivel logico. As tensoes sao dado bruto: com");
  Serial.println("  pull-up interno de 45k o ADC carrega o pino e o numero nao");
  Serial.println("  distingue pino vazio de carga - nao tire conclusao dele.");
  Serial.println();
  Serial.println("  pino               pull-up      pull-down    veredito");
  Serial.println("  ----------------------------------------------------------------");

  for (int i = 0; i < N; i++) {
    const PinoInfo& p = PINOS[i];
    Perfil& r = perfis[i];

    if (p.saida) {
      pinMode(p.gpio, INPUT_PULLUP);   delay(8);
      r.nUp = digitalRead(p.gpio);
      if (p.adc) r.mvUp = mediaMv(p.gpio, 16);
      pinMode(p.gpio, INPUT_PULLDOWN); delay(8);
      r.nDn = digitalRead(p.gpio);
      if (p.adc) r.mvDn = mediaMv(p.gpio, 16);
      pinMode(p.gpio, INPUT);

      if (r.nUp == HIGH && r.nDn == LOW) {
        r.veredito = "livre, ou carga que nao conduz em continua (buzzer, capacitor)";
      } else if (r.nUp == HIGH && r.nDn == HIGH) {
        r.veredito = "puxado para o 3V3 (pull-up de modulo, ou fio no 3V3)";
        r.seguro   = false;
      } else if (r.nUp == LOW && r.nDn == LOW) {
        // Pode ser fio ao terra (nao dirigir) ou bobina/LED (pode acionar).
        if (p.adc) {
          r.mvCarga = tensaoSobCarga(p.gpio);
          if (r.mvCarga > 500) {
            r.veredito   = "carga de baixa resistencia ate o terra (bobina, LED)";
            r.cargaBaixa = true;
            r.seguro     = false;   // so tom, nunca nivel continuo
          } else {
            r.veredito = "AMARRADO NO TERRA (fio direto) - nao sera dirigido";
            r.seguro   = false;
          }
        } else {
          r.veredito = "puxado para o terra - nao sera dirigido";
          r.seguro   = false;
        }
      } else {
        r.veredito = "instavel";
        r.seguro   = false;
      }
    } else {
      pinMode(p.gpio, INPUT);
      r.mvUp = r.mvDn = mediaMv(p.gpio, 32);
      r.nUp  = r.nDn  = (r.mvUp > 1650);
      r.veredito = "entrada analogica - ver fase 5";
      r.seguro   = false;
    }

    char loc[24]; ondeFica(i, loc, sizeof loc);
    Serial.printf("  %-18s ", loc);
    if (p.adc) Serial.printf("%d/%4d mV   %d/%4d mV   %s\n", r.nUp, r.mvUp, r.nDn, r.mvDn, r.veredito);
    else       Serial.printf("%d           %d           %s\n", r.nUp, r.nDn, r.veredito);
    if (r.mvCarga >= 0)
      Serial.printf("  %-18s sustenta %d mV sob carga (curto franco cairia abaixo de 500)\n", "", r.mvCarga);
  }
}

// ---------------------------------------------------------------------------
// FASE 2 - quem esta ligado em quem.
void fase2_ligacoes() {
  titulo("FASE 2 - LIGACOES ENTRE PINOS (jumpers e linhas em comum)");
  memset(conectado, 0, sizeof conectado);

  bool baixo[N];
  int  mvBaixo[N];

  for (int i = 0; i < N; i++) {
    if (!PINOS[i].saida || !perfis[i].seguro) continue;

    pinMode(PINOS[i].gpio, OUTPUT);
    digitalWrite(PINOS[i].gpio, LOW);
    delay(6);
    for (int j = 0; j < N; j++) {
      if (j == i) continue;
      if (PINOS[j].saida) {
        pinMode(PINOS[j].gpio, INPUT_PULLUP); delay(3);
        baixo[j] = (digitalRead(PINOS[j].gpio) == LOW);
      } else {
        mvBaixo[j] = mediaMv(PINOS[j].gpio, 8);
      }
    }

    digitalWrite(PINOS[i].gpio, HIGH);
    delay(6);
    for (int j = 0; j < N; j++) {
      if (j == i) continue;
      if (PINOS[j].saida) {
        pinMode(PINOS[j].gpio, INPUT_PULLDOWN); delay(3);
        bool alto = (digitalRead(PINOS[j].gpio) == HIGH);
        // So conta se o pino SEGUIU o driver nos dois sentidos: um pino preso
        // em 1 ou em 0 nao acompanha, e nao vira falso positivo.
        if (alto && baixo[j]) conectado[i][j] = true;
      } else {
        int mvAlto = mediaMv(PINOS[j].gpio, 8);
        if (mvAlto - mvBaixo[j] > 1200) conectado[i][j] = true;
      }
      pinMode(PINOS[j].gpio, INPUT);
    }
    pinMode(PINOS[i].gpio, INPUT);
  }

  int achados = 0;
  for (int i = 0; i < N; i++)
    for (int j = i + 1; j < N; j++)
      if (conectado[i][j] || conectado[j][i]) {
        char a[24], b[24]; ondeFica(i, a, sizeof a); ondeFica(j, b, sizeof b);
        Serial.printf("  %s  <-->  %s\n", a, b);
        achados++;
      }
  if (achados == 0) Serial.println("  Nenhum par de pinos esta ligado entre si.");
}

// ---------------------------------------------------------------------------
// FASE 3 - 1-Wire sem saber onde esta o barramento.
// VEM ANTES DO I2C de proposito - ver erro (a) no topo do arquivo.
void fase3_onewire() {
  titulo("FASE 3 - VARREDURA 1-WIRE (roda ANTES do I2C, ver nota no topo)");
  int achados = 0;

  for (int i = 0; i < N; i++) {
    if (!PINOS[i].saida) continue;
    if (perfis[i].nUp == LOW) continue;     // linha presa em baixo: nao ha 1-Wire
    gpio_reset_pin((gpio_num_t)PINOS[i].gpio);

    OneWire ow(PINOS[i].gpio);
    if (!ow.reset()) continue;

    uint8_t rom[8];
    ow.reset_search();
    while (ow.search(rom)) {
      if (OneWire::crc8(rom, 7) != rom[7]) continue;  // ruido, nao dispositivo
      char loc[24]; ondeFica(i, loc, sizeof loc);
      Serial.printf("  %s  ROM ", loc);
      for (int b = 0; b < 8; b++) Serial.printf("%02X", rom[b]);
      if      (rom[0] == 0x28) Serial.print("   <- DS18B20");
      else if (rom[0] == 0x10) Serial.print("   <- DS18S20");
      else if (rom[0] == 0x22) Serial.print("   <- DS1822");
      Serial.println();
      achados++;
    }

    // Pergunta ao proprio sensor se o VDD chegou nele (SKIP ROM + 0xB4).
    if (achados > 0) {
      ow.reset(); ow.skip(); ow.write(0xB4);
      int alimentado = ow.read_bit();
      Serial.printf("  alimentacao (0xB4): %d %s\n", alimentado,
                    alimentado ? "= VDD externo presente"
                               : "= MODO PARASITA, o VDD nao chega ao sensor");
    }
    pinMode(PINOS[i].gpio, INPUT);
  }
  if (achados == 0) {
    Serial.println("  Nenhum dispositivo 1-Wire respondeu em pino nenhum.");
    Serial.println("  -> sensor sem 3V3/GND, fio de dados solto, ou sem o pull-up de 4,7k.");
  }
}

// ---------------------------------------------------------------------------
// FASE 4 - I2C sem saber onde esta o barramento.
void fase4_i2c() {
  titulo("FASE 4 - VARREDURA I2C (descobre SDA, SCL e o endereco)");

  int cand[N], nc = 0;
  for (int i = 0; i < N; i++)
    if (PINOS[i].saida && perfis[i].nUp == HIGH && perfis[i].nDn == HIGH) cand[nc++] = i;

  if (nc < 2) {
    Serial.println("  Nenhum par com cara de barramento I2C (pull-up externo nos dois).");
    Serial.println("  Caindo para a busca ampla nos pinos utilizaveis.");
    nc = 0;
    for (int i = 0; i < N; i++)
      if (PINOS[i].saida && perfis[i].nUp == HIGH) cand[nc++] = i;
  } else {
    Serial.printf("  %d pinos com pull-up externo - testando os pares entre eles.\n", nc);
  }

  int achados = 0;
  for (int a = 0; a < nc && achados == 0; a++) {
    for (int b = 0; b < nc && achados == 0; b++) {
      if (a == b) continue;
      uint8_t sda = PINOS[cand[a]].gpio, scl = PINOS[cand[b]].gpio;
      Wire.end();
      if (!Wire.begin(sda, scl, 100000)) continue;
      Wire.setTimeOut(10);
      for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() != 0) continue;
        char sa[24], sb[24]; ondeFica(cand[a], sa, sizeof sa); ondeFica(cand[b], sb, sizeof sb);
        Serial.printf("  RESPONDEU 0x%02X  com SDA=%s  SCL=%s", addr, sa, sb);
        if (addr == 0x3C || addr == 0x3D) Serial.print("   <- display SSD1306");
        Serial.println();
        i2cSda = cand[a]; i2cScl = cand[b];
        achados++;
      }
      Wire.end();
      // Sem isto o driver do I2C fica pendurado no pino e quebra qualquer uso
      // posterior dele. Foi exatamente o que escondeu o DS18B20 - ver erro (a).
      gpio_reset_pin((gpio_num_t)sda);
      gpio_reset_pin((gpio_num_t)scl);
    }
  }
  if (achados == 0) {
    Serial.println("  NADA respondeu em nenhum par testado.");
    Serial.println("  -> modulo sem 3V3/GND, ou os dois fios de dados fora do lugar.");
  }
}

// ---------------------------------------------------------------------------
// FASE 5 - o que as entradas analogicas estao vendo.
void fase5_analogicas() {
  titulo("FASE 5 - ENTRADAS ANALOGICAS (64 amostras cada)");
  Serial.println("  pino                media     min      max     amplitude  leitura");
  Serial.println("  ----------------------------------------------------------------------");

  for (int i = 0; i < N; i++) {
    if (!PINOS[i].adc) continue;
    pinMode(PINOS[i].gpio, INPUT);
    analogSetPinAttenuation(PINOS[i].gpio, ADC_11db);
    int mn = 4000, mx = 0; uint32_t soma = 0;
    for (int a = 0; a < 64; a++) {
      int v = analogReadMilliVolts(PINOS[i].gpio);
      soma += v; if (v < mn) mn = v; if (v > mx) mx = v;
      delayMicroseconds(300);
    }
    int media = soma / 64, amp = mx - mn;

    const char* leitura;
    if (media < 80)        leitura = "no terra";
    else if (media > 3150) leitura = "no teto (3,3 V)";
    else if (amp > 250)    leitura = "flutuando - provavelmente nada ligado";
    else                   leitura = "FONTE FIRME - tem sensor ligado aqui";

    char loc[24]; ondeFica(i, loc, sizeof loc);
    Serial.printf("  %-18s %5d mV %5d mV %5d mV %6d mV  %s\n", loc, media, mn, mx, amp, leitura);
  }
}

// ---------------------------------------------------------------------------
// FASE 6 - atuadores. A unica parte que precisa de alguem olhando.
void fase6_atuadores() {
  titulo("FASE 6 - VARREDURA DAS SAIDAS: olhe e ouca a bancada");
  Serial.println("  Anote o NUMERO em que algo acender, clicar ou apitar.");
  if (i2cSda >= 0)
    Serial.println("  (os dois pinos do barramento I2C ficam de fora, para nao derrubar o display)");
  Serial.println();

  for (int i = 0; i < N; i++) {
    if (!PINOS[i].saida) continue;
    if (i == i2cSda || i == i2cScl) continue;
    if (!perfis[i].seguro && !perfis[i].cargaBaixa) continue;

    char loc[24]; ondeFica(i, loc, sizeof loc);
    Serial.printf("  [%02d] %s : ", i, loc);

    if (perfis[i].cargaBaixa) {
      // Bobina: so tom. Nivel continuo passaria de 40 mA no pino.
      Serial.print("tom (carga de baixa resistencia)...");
      tone(PINOS[i].gpio, 2000, 700); delay(900); noTone(PINOS[i].gpio);
    } else {
      Serial.print("alto...");
      pinMode(PINOS[i].gpio, OUTPUT);
      digitalWrite(PINOS[i].gpio, HIGH); delay(1500);
      Serial.print(" baixo...");
      digitalWrite(PINOS[i].gpio, LOW);  delay(1500);
      Serial.print(" tom...");
      tone(PINOS[i].gpio, 2000, 700);    delay(900);
      noTone(PINOS[i].gpio);
    }
    pinMode(PINOS[i].gpio, INPUT);
    Serial.println(" ok");
    delay(400);
  }
  Serial.println("  --- fim da varredura, recomecando em 5 s ---");
}

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println();
  Serial.println("### MAPA CEGO DA BANCADA - nada aqui parte do mapa documentado ###");
  fase1_assinatura();
  fase2_ligacoes();
  fase3_onewire();     // 1-Wire ANTES do I2C - ver erro (a) no topo
  fase4_i2c();
  fase5_analogicas();
  Serial.println();
  Serial.println("### FIM DAS VARREDURAS AUTOMATICAS ###");
}

void loop() {
  fase6_atuadores();
  delay(5000);
}
