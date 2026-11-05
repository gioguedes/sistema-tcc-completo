// Varredura das redes 2,4 GHz visiveis pelo ESP32.
// Serve para descobrir o SSID EXATO (maiuscula, espaco ou acento errado nao
// conecta), medir o sinal no lugar da bancada e -- o motivo de existir a coluna
// bssid -- identificar QUAL aparelho emite cada rede.
//
// Por que o bssid importa aqui: a casa tem dois roteadores em cascata. O PC esta
// por cabo atras do 192.168.2.1 (MAC c6:84:fc:30:5e:64), que NATeia para a rede
// 192.168.15.x. Um no na rede 15 nao alcanca o PC. Comparando o bssid de cada AP
// com o MAC do gateway descobrimos qual SSID pertence ao aparelho do PC, sem
// precisar tentar senha em rede de terceiro.
// O ESP32 so tem radio 2,4 GHz: tudo que aparecer aqui ele consegue usar.
#include <WiFi.h>

// MAC da interface cabeada do gateway do PC. Os radios de um mesmo aparelho
// costumam ficar no mesmo bloco, variando os ultimos bytes.
const char* MAC_GATEWAY_PC = "c6:84:fc:30:5e:64";

void setup() {
  Serial.begin(115200);
  delay(300);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  Serial.println();
  Serial.printf("=== Varredura 2,4 GHz (MAC do gateway do PC: %s) ===\n", MAC_GATEWAY_PC);
  int n = WiFi.scanNetworks();
  if (n <= 0) {
    Serial.println("Nenhuma rede encontrada (roteador longe ou desligado?).");
    return;
  }
  Serial.printf("%d redes:\n", n);
  for (int i = 0; i < n; i++) {
    // rssi: -30 excelente, -67 bom, -80 ruim, -90 inutilizavel.
    Serial.printf("%2d) %-24s bssid=%s rssi=%4d dBm canal=%2d %s\n", i + 1,
                  WiFi.SSID(i).c_str(), WiFi.BSSIDstr(i).c_str(), WiFi.RSSI(i),
                  WiFi.channel(i),
                  WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "aberta" : "com senha");
  }
  Serial.println("=== fim da varredura ===");
}

void loop() { delay(1000); }
