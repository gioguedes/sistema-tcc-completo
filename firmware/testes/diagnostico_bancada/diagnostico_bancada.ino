// Inventario da bancada: descobre sozinho o que esta ligado em cada pino.
// Roda 4 varreduras automaticas no boot e depois fica acionando as saidas
// uma a uma, para localizar LED / buzzer / rele pelo que voce ve e ouve.
//
// Serial Monitor a 115200 baud. Nenhum teste aciona dois pinos ao mesmo tempo
// e nenhum coloca um pino em OUTPUT durante as leituras — nao ha risco de curto.
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// Pinos que podem ser entrada E saida (tem pull-up/pull-down internos).
const int pinosIO[]   = {32, 33, 25, 26, 27, 14, 12, 13};
const char* nomeIO[]  = {"OLED SCL", "OLED SDA", "DS18B20", "rele IN",
                         "livre", "livre", "buzzer", "LED status"};
// Somente entrada: sem pull interno, so leitura analogica.
const int pinosADC[]  = {36, 39, 34, 35};
const char* nomeADC[] = {"vp/36 (livre)", "vn/39 (livre)", "turbidez", "pH"};

const int nIO  = sizeof(pinosIO) / sizeof(pinosIO[0]);
const int nADC = sizeof(pinosADC) / sizeof(pinosADC[0]);

void titulo(const char* t) {
  Serial.println();
  Serial.println("==================================================");
  Serial.println(t);
  Serial.println("==================================================");
}

// ---------- 1) Quem responde no barramento I2C ----------
void varrerI2C() {
  titulo("1) BARRAMENTO I2C (SDA=33, SCL=32)");
  Wire.begin(33, 32);
  int achados = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  dispositivo em 0x%02X", addr);
      if (addr == 0x3C || addr == 0x3D) Serial.print("  <- OLED SSD1306");
      Serial.println();
      achados++;
    }
  }
  if (achados == 0) {
    Serial.println("  NENHUM dispositivo respondeu.");
    Serial.println("  -> OLED sem alimentacao, ou SDA/SCL trocados ou soltos.");
  }
}

// ---------- 2) Quem responde no barramento 1-Wire ----------
void varrer1Wire() {
  titulo("2) BARRAMENTO 1-WIRE (GPIO25)");
  OneWire ow(25);
  DallasTemperature ds(&ow);
  ds.begin();
  int n = ds.getDeviceCount();
  Serial.printf("  sensores encontrados: %d\n", n);
  if (n == 0) {
    Serial.println("  -> DS18B20 solto, sem 3V3, ou faltando o pull-up de 4,7k.");
    return;
  }
  DeviceAddress addr;
  for (int i = 0; i < n; i++) {
    if (!ds.getAddress(addr, i)) continue;
    Serial.printf("  [%d] endereco ", i);
    for (uint8_t b = 0; b < 8; b++) Serial.printf("%02X", addr[b]);
    Serial.println();
  }
  ds.getAddress(addr, 0);

  // Pergunta ao proprio sensor se ele esta sendo alimentado. Em modo parasita
  // ele responde ao barramento (ROM sai correta) mas nao tem energia para
  // converter, e a temperatura volta -127. Isso separa falha de fio de
  // qualquer outra causa, sem depender de palpite.
  bool parasita = ds.isParasitePowerMode();
  Serial.print("  alimentacao: ");
  Serial.println(parasita ? "MODO PARASITA <- o VDD nao chega ao sensor"
                          : "VDD presente (alimentacao externa OK)");
  Serial.printf("  resolucao lida do scratchpad: %d bits", ds.getResolution(addr));
  Serial.println(" (0 = scratchpad ilegivel)");

  // Tres tentativas: a primeira leitura apos o power-up costuma ser a pior.
  for (int tent = 1; tent <= 3; tent++) {
    ds.requestTemperatures();
    float t = ds.getTempC(addr);
    Serial.printf("  tentativa %d: %.2f C", tent, t);
    if (t == DEVICE_DISCONNECTED_C) Serial.print("  <- INVALIDA (CRC do scratchpad falhou)");
    else if (t >= 85.0f)            Serial.print("  <- 85.00 = valor de fabrica, nao converteu");
    Serial.println();
    delay(1000);
  }
}

// ---------- 3) Tensao nas entradas analogicas ----------
void lerAnalogicos() {
  titulo("3) ENTRADAS ANALOGICAS (media de 32 amostras)");
  for (int i = 0; i < nADC; i++) {
    analogSetPinAttenuation(pinosADC[i], ADC_11db);
    uint32_t soma = 0;
    for (int a = 0; a < 32; a++) { soma += analogReadMilliVolts(pinosADC[i]); delayMicroseconds(200); }
    float mv = soma / 32.0f;
    Serial.printf("  GPIO%-3d %-16s %6.0f mV", pinosADC[i], nomeADC[i], mv);
    if (mv < 60)        Serial.print("  <- no terra ou nada ligado");
    else if (mv > 3000) Serial.print("  <- perto do teto (3,3 V)");
    Serial.println();
  }
  Serial.println();
  Serial.println("  Referencia da bancada: pH ~1900 mV com o eletrodo na garrafinha");
  Serial.println("  (se der ~300 mV instavel, o BNC do eletrodo esta solto).");
  Serial.println("  Turbidez ~1300 mV no pino = ~2600 mV reais (divisor 4,7k+4,7k).");
}

// ---------- 4) O que cada pino digital enxerga ----------
// Le o pino com pull-up e depois com pull-down (nunca como saida).
// Preso em 1 = amarrado ao 3V3. Preso em 0 = amarrado ao terra.
// Acompanha o pull = livre, ou ligado a algo de alta impedancia.
void testarAmarracao() {
  titulo("4) AMARRACAO DOS PINOS DIGITAIS");
  Serial.println("  pino  esperado          com pull-up  com pull-down  veredito");
  for (int i = 0; i < nIO; i++) {
    pinMode(pinosIO[i], INPUT_PULLUP);
    delay(5);
    int comUp = digitalRead(pinosIO[i]);
    pinMode(pinosIO[i], INPUT_PULLDOWN);
    delay(5);
    int comDown = digitalRead(pinosIO[i]);
    pinMode(pinosIO[i], INPUT);

    const char* veredito;
    if (comUp == HIGH && comDown == LOW)      veredito = "livre / alta impedancia";
    else if (comUp == HIGH && comDown == HIGH) veredito = "PRESO EM 3V3";
    else if (comUp == LOW  && comDown == LOW)  veredito = "PRESO NO TERRA";
    else                                       veredito = "instavel";

    Serial.printf("  %-5d %-17s %-12d %-14d %s\n",
                  pinosIO[i], nomeIO[i], comUp, comDown, veredito);
  }
  Serial.println();
  Serial.println("  PRESO EM 3V3 ou PRESO NO TERRA num pino que deveria estar livre");
  Serial.println("  = jumper na linha errada. LED e buzzer aparecem como 'livre'.");
}

// ---------- 5) Varredura das saidas ----------
void varrerSaidas() {
  titulo("5) VARREDURA DAS SAIDAS — olhe e ouca a bancada");
  Serial.println("  Cada pino fica 3 s ativo. Anote em qual deles algo acontece.");
  Serial.println("  LED: acende. Buzzer: apita. Rele: clica (arma em LOW).");
  Serial.println();

  for (int i = 0; i < nIO; i++) {
    int p = pinosIO[i];
    if (p == 32 || p == 33) continue;  // I2C do OLED: nao mexer

    Serial.printf(">>> GPIO %-3d (%s): HIGH por 3 s\n", p, nomeIO[i]);
    pinMode(p, OUTPUT);
    digitalWrite(p, HIGH);
    delay(3000);
    Serial.printf("    GPIO %-3d: LOW por 3 s (o rele arma aqui)\n", p);
    digitalWrite(p, LOW);
    delay(3000);
    pinMode(p, INPUT);   // devolve a alta impedancia antes do proximo
    delay(300);
  }
  Serial.println("--- fim da varredura ---");
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("### DIAGNOSTICO DA BANCADA — no sensor ###");
  varrerI2C();
  varrer1Wire();
  lerAnalogicos();
  testarAmarracao();
}

void loop() {
  varrerSaidas();
  delay(2000);
}
