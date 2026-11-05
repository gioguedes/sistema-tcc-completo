// Diagnostico: descobre em qual GPIO o jumper IN do rele esta espetado.
// Varre os pinos de saida da fileira acessivel, um por vez, 3 s em LOW cada.
// Modulo e ativo-baixo: quando o pino certo ficar LOW, o rele arma
// (clique + LED verde). Anotar o numero mostrado no Serial nesse momento.
// Nao inclui SD2/SD3/CMD (flash) nem 34/35/36/39 (input-only).

const int pinos[] = {32, 33, 25, 26, 27, 14, 12, 13};
const int n = sizeof(pinos) / sizeof(pinos[0]);

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < n; i++) {
    pinMode(pinos[i], OUTPUT);
    digitalWrite(pinos[i], HIGH);  // HIGH = rele desarmado
  }
  Serial.println("Varredura de pinos — observe quando o rele clicar");
}

void loop() {
  for (int i = 0; i < n; i++) {
    Serial.printf(">>> GPIO %d em LOW agora\n", pinos[i]);
    digitalWrite(pinos[i], LOW);
    delay(3000);
    digitalWrite(pinos[i], HIGH);
    delay(500);
  }
  Serial.println("--- fim da varredura, recomecando ---");
}
