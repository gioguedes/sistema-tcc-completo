// Diagnostico do circuito do LED de status, quando a topologia relatada e a medicao
// de continuidade discordam (bancada de 23/08/2026).
//
// Nao sobe Wi-Fi de proposito: alem de nao precisar, o radio e o que estava
// derrubando a placa por brownout durante o diagnostico.
//
// O que ele responde, em ordem:
//   1. Existe caminho ate o terra a partir de ALGUM pino da fileira acessivel?
//      Se existir num pino diferente do 13, o jumper esta no furo errado.
//      Se nao existir em nenhum, o contato do resistor ou do terra e que e ruim.
//   2. O driver de saida do GPIO13 sobreviveu ao periodo em que acionou o LED sem
//      resistor limitador? (escreve e le de volta o proprio pino)
#include <Arduino.h>

const int PINO_LED = 13;

// Pinos da fileira que o usuario usa, na ordem fisica das linhas da protoboard.
// Faltam de proposito: SD2/SD3/CMD (linhas 34-36) sao a flash e nao se toca; e
// GPIO34-39 nao tem pull-up/pull-down interno, entao este teste nao se aplica a eles.
struct Candidato { int linha; int gpio; const char* esperado; };
const Candidato CANDIDATOS[] = {
  { 33, 13, "0 SE o circuito do LED estiver fechado (este e o alvo)" },
  { 31, 12, "1 (buzzer passivo nao da caminho DC)" },
  { 30, 14, "1 (pino livre)" },
  { 29, 27, "1 (pino livre)" },
  { 28, 26, "depende do modulo rele (entrada optoacoplada)" },
  { 27, 25, "1 (pull-up de 4,7k do DS18B20 puxa para 3V3)" },
  { 26, 33, "1 (pull-up do modulo OLED)" },
  { 25, 32, "1 (pull-up do modulo OLED)" },
};
const int N_CANDIDATOS = sizeof(CANDIDATOS) / sizeof(CANDIDATOS[0]);

// Com pull-up interno (~45 kOhm), qualquer caminho externo ate o terra de ate
// alguns kOhm derruba o pino para perto de 0 V e o digitalRead devolve 0.
// Um resistor de 330R ate o terra deixa o pino em ~24 mV: le 0 sem ambiguidade.
bool temCaminhoParaTerra(int gpio) {
  pinMode(gpio, INPUT_PULLUP);
  delay(20);
  return digitalRead(gpio) == 0;
}

void varrerPinos() {
  Serial.println();
  Serial.println("== 1. Onde existe caminho ate o terra ==");
  Serial.println("linha  gpio  leu  veredito");
  int achados = 0;
  for (int i = 0; i < N_CANDIDATOS; i++) {
    int gpio = CANDIDATOS[i].gpio;
    pinMode(gpio, INPUT_PULLUP);
    delay(20);
    int comUp = digitalRead(gpio);
    if (comUp == 0) achados++;
    Serial.printf("  %2d   %4d   %d   %s   [esperado: %s]\n",
                  CANDIDATOS[i].linha, gpio, comUp,
                  comUp == 0 ? "CAMINHO ATE O TERRA" : "sem caminho        ",
                  CANDIDATOS[i].esperado);
  }
  Serial.printf("\nPinos com caminho ate o terra: %d\n", achados);
  if (achados == 0) {
    Serial.println("=> NENHUM pino ve o resistor. O rompimento esta no contato do resistor");
    Serial.println("   (furo 53h ou 48i) ou no aterramento da linha 48, nao no jumper.");
  }
}

// Se o pad sofreu com a corrente sem limite, isso aparece aqui: pino configurado
// como saida no ESP32 devolve no digitalRead o nivel real do pino, entao escrever
// 1 e ler 0 denuncia driver incapaz de sustentar o nivel (ou curto para o terra).
void testarDriverDoPino13() {
  Serial.println();
  Serial.println("== 2. O driver do GPIO13 esta vivo? ==");
  pinMode(PINO_LED, OUTPUT);
  int falhas = 0;
  for (int i = 0; i < 5; i++) {
    digitalWrite(PINO_LED, HIGH);
    delayMicroseconds(50);
    int lidoAlto = digitalRead(PINO_LED);
    digitalWrite(PINO_LED, LOW);
    delayMicroseconds(50);
    int lidoBaixo = digitalRead(PINO_LED);
    if (lidoAlto != 1 || lidoBaixo != 0) falhas++;
    Serial.printf("  tentativa %d: escrevi 1 li %d | escrevi 0 li %d\n", i + 1, lidoAlto, lidoBaixo);
  }
  Serial.println(falhas == 0 ? "  => driver OK (o pino sustenta os dois niveis)"
                             : "  => DRIVER SUSPEITO (o pino nao sustenta o nivel escrito)");
}

// Deixa o pino aceso fixo por um tempo longo: se o circuito estiver bom, isso e
// visivel na bancada sem depender de pegar um pisca de 0,7 s no olho.
void acenderFixo(int segundos) {
  Serial.println();
  Serial.printf("== 3. GPIO13 em nivel alto por %d s -- OLHE A BANCADA ==\n", segundos);
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, HIGH);
  delay((unsigned long)segundos * 1000UL);
  digitalWrite(PINO_LED, LOW);
  Serial.println("  fim (pino de volta para nivel baixo)");
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println("=== diagnostico_led -- sem Wi-Fi, sem MQTT ===");
  varrerPinos();
  testarDriverDoPino13();
  acenderFixo(10);
  Serial.println();
  Serial.println("=== fim do diagnostico ===");
}

void loop() {
  delay(1000);
}
