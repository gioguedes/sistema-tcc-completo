# Mapa da bancada (protoboard) — nó sensor

Atualizado em: 2026-08-24

## Placa

- **ESP32 DevKitC 38 pinos** (chip ESP32-D0WD-V3, MAC `a4:f0:0f:64:3c:70`), gravação na porta **COM3**, placa "ESP32 Dev Module" no Arduino IDE (⚠️ não selecionar variantes S2/S3/C3).
- Espetada na protoboard (colunas a–j). Fileira acessível de pinos na **coluna i**; furos livres na **coluna j**.
- Mapeamento linha ↔ pino (fileira acessível):

| Linha | Pino | Linha | Pino |
|---|---|---|---|
| 1 | 5v | 11 | **25 (DS18B20)** |
| 2 | CMD ⚠️ flash — NÃO USAR | 12 | 33 (SDA OLED) |
| 3 | SD3 ⚠️ flash — NÃO USAR | 13 | 32 (SCL OLED) |
| 4 | SD2 ⚠️ flash — NÃO USAR | 14 | **35 (pH)** |
| 5 | **13 (LED de status)** | 15 | **34 (turbidez)** |
| 6 | gnd | 16 | vn (39) |
| 7 | **12 (buzzer)** | 17 | vp (36) |
| 8 | 14 (livre) | 18 | en |
| 9 | 27 (livre) | 19 | 3v3 |
| 10 | **26 (relé)** | | |

> ⚠️ **Esta tabela foi corrigida em 2026-08-23, conferida pino a pino contra a serigrafia
> da placa.** A versão anterior listava os pinos nas linhas 19–37, numerados no sentido
> **oposto** ao real. Só o `3v3` coincidia, por ser a linha onde as duas contagens se
> cruzam — o que fez o erro passar despercebido por sete semanas. Conversão da planta
> antiga para esta: `linha_correta = 38 − linha_antiga`.
>
> O custo do erro: uma sessão inteira de diagnóstico do LED de status. A "linha 33" que a
> planta chamava de GPIO13 é, na verdade, a linha da segunda perna do **buzzer**, e todas
> as tentativas de montar o LED foram feitas penduradas nela.

## Montagem atual

> **Mapa levantado furo a furo pelo usuário em 2026-08-24**, e cruzado com a varredura
> elétrica cega do sketch `firmware/testes/mapa_bancada`. As duas fontes — planta e
> medição — batem em **todos** os pinos. É a primeira versão deste documento com
> confirmação independente; a tabela anterior era só planta.

**Trilho de terra: linha 60** (ligada ao gnd do ESP via 60h→6j). Linha **cheia**.
**Trilho de 3,3 V: linha 56** (ligada ao 3V3 via 55i→56i, criado em 2026-07-09). 2 furos livres.
**Taps de terra livres:** linha **36** (terra via 36i→42h; furos f, g, h vagos) e **48i**.

### Coluna j — o que sai de cada pino do ESP32

A fileira acessível está na coluna **i**; a coluna **j** é o mesmo nó elétrico e recebe os jumpers.

| Furo | Pino | Vai para |
|---|---|---|
| 1j | 5v | 40g — VCC da placa de turbidez |
| 2j / 3j / 4j | CMD / SD3 / SD2 | ⚠️ flash — vazios, NÃO USAR |
| **5j** | **13** | 44j — LED de status, **montado em 2026-08-24** |
| 6j | gnd | 60h — trilho de terra |
| 7j | **12** | 30i — uma perna do buzzer |
| 8j / 9j | 14 / 27 | vazios (livres) |
| 10j | **26** | pino **IN** do módulo de relé (fêmea-macho) |
| 11j | **25** | 50h — dados do DS18B20 |
| 12j | **33** | pino **SDA** do OLED |
| 13j | **32** | pino **SCL** do OLED |
| 14j | **35** | pino **A** (sinal) da placa de pH |
| 15j | **34** | 45f — nó do divisor da turbidez |
| 16j / 17j / 18j | vn (39) / vp (36) / en | vazios |
| 19j | 3v3 | 55h — linha de 3,3 V |

### Demais linhas

| Linha | O quê |
|---|---|
| 30 | **30f** = perna do buzzer; **30i** ← jumper do 7j (GPIO12) |
| 33 | **33f** = outra perna do buzzer; **33j → 36j** (terra) — corrigido em 24/08, ver abaixo |
| 36 | Tap de terra: **36i → 42h**; **36j** ← 33j (retorno do buzzer). Livres: 36f, 36g, 36h |
| 40 | **40f** = VCC da placa de turbidez; **40g** ← 1j (5v) |
| 41 | **41f** = OUT da placa de turbidez; **41g → 45g** (resistor 4,7 kΩ, topo do divisor) |
| 42 | **42f** = GND da placa de turbidez. **Cheia:** 42g→60i, 42h→36i, 42i→GND do OLED, 42j→**−** da placa de pH |
| 44 | **44j** ← 5j (GPIO13); **44i → 46i** (resistor 330 Ω do LED) |
| 45 | Nó do divisor: **45f → 15j** (GPIO34, **fator 2,0 no código**), 45g ← resistor do 41g, **45h → 48h** (resistor 4,7 kΩ) |
| 46 | **46j** = perna **longa** do LED de status; **46i** ← resistor do 44i |
| 48 | Base do divisor: **48g → 60g** (terra). **48j** = perna **curta** do LED. Livre: 48i |
| 50 | **50f** = fio **AMARELO** (dados) do DS18B20; **50g → 55g** (resistor 4,7 kΩ, pull-up 1-Wire); **50h → 11j** |
| 55 | **55f** = fio **VERMELHO** (VDD) do DS18B20. **Cheia:** 55g ← resistor do 50g, 55h→19j (3V3), 55i→56i, 55j→**+** da placa de pH |
| 56 | Trilho de 3,3 V: **56h** → VCC do relé, **56i** ← 55i, **56j** → VCC do OLED. Livres: 56f, 56g |
| 60 | **60f** = fio **PRETO** (GND) do DS18B20. **Cheia:** 60g→48g, 60h→6j (gnd), 60i→42g, 60j→GND do relé |
| 62 | **62i** = jumper com a outra ponta solta — ⚠️ **remover**, é ponta viva à toa |
| — | Eletrodo de pH rosqueado no BNC da placa Gravity (⚠️ conferir se travou: BNC solto lê ~300 mV instável) |

### Correções que este levantamento trouxe (2026-08-24)

1. **O buzzer estava com o circuito aberto — CORRIGIDO no mesmo dia.** Ele vai do GPIO12
   (7j → 30i) à linha 30, atravessa para a linha 33, e de lá o jumper roxo ia para **53i** —
   e a linha 53 não tem mais nada. Sem retorno ao terra, `tone()` não produzia som algum. A
   versão anterior deste documento registrava esse jumper como `33j → 51i` e supunha ser
   "provável retorno do buzzer"; era suposição, e estava errada nos dois números.
   **Correção aplicada:** a ponta saiu de `53i` e foi para **`36j`** (linha 36 = terra via
   36i→42h). Buzzer apitou na hora. O GPIO12 passou a ler 134 mV com pull-up (antes flutuava
   em 2554 mV), o que confirma o caminho fechado pela bobina.
2. **A placa da turbidez ocupa 40f/41f/42f**, não 41f/42f/43f como dizia a linha final da
   tabela antiga (que contradizia a primeira linha da mesma tabela).
3. **A linha 36 é um tap de terra** (36i→42h) e não constava em lugar nenhum.
4. O `42h` estava documentado como "perninha − do buzzer"; na verdade vai para o tap de terra 36i.

### Conferência cruzada com a varredura elétrica (2026-08-24)

Medições de `firmware/testes/mapa_bancada`, com a placa em bancada e sem Wi-Fi:

| Pino | Medido | Bate com a planta? |
|---|---|---|
| GPIO33 / GPIO32 | I2C respondeu `0x3C` com SDA=33, SCL=32 | ✅ OLED |
| GPIO35 | 1810 mV, amplitude 75 mV (fonte firme) | ✅ pH |
| GPIO34 | 1299 mV, amplitude 32 mV (fonte firme) | ✅ turbidez, nó do divisor |
| GPIO26 | 2858 mV firme = pull-up do módulo | ✅ relé |
| GPIO25 | ROM `282061B10000006A`, CRC ok, `0xB4`=1 (VDD presente), 22,12 °C | ✅ DS18B20 |
| GPIO13 | ver nota abaixo | ✅ LED de status, aceso |
| GPIO12 | 134 mV com pull-up (após a correção do jumper) | ✅ buzzer, circuito fechado |
| GPIO14, 27, 39, 36 e toda a 2ª fileira | flutuando | ✅ vazios |

Nenhum par de pinos do ESP32 aparece ligado entre si — coerente com a planta, em que todo
jumper vai de um pino para uma linha da protoboard, nunca de pino a pino.

> ⚠️ **Retratação (2026-08-24):** durante três varreduras seguidas o DS18B20 apareceu como
> "nenhum dispositivo 1-Wire respondeu", e este documento chegou a registrá-lo como mudo. Era
> **defeito da ferramenta, não da bancada**: o `mapa_bancada` rodava a varredura I2C antes da
> 1-Wire, e no ESP32 o `pinMode()` não desfaz o roteamento da matriz de periféricos — o driver
> do I2C continuava pendurado no GPIO25 e prendia a linha. Provado por `diagnostico_1wire`,
> que faz o reset na mão: pulso de presença dentro da norma (início 30 µs, duração 100 µs),
> ROM com CRC válido, e 22,12 °C. O sketch foi corrigido (1-Wire primeiro + `gpio_reset_pin()`
> depois de cada `Wire.end()`). **Lição:** antes de mandar mexer no hardware, provar que a
> ferramenta de medição não é a causa — dois reencaixes de fio foram pedidos à toa.

**Oito de oito componentes validados em 2026-08-24 — bancada completa pela primeira vez.**
OLED, pH, turbidez, relé, DS18B20 e buzzer conferidos eletricamente; LED de status montado e
**aceso**, com a tela mostrando as leituras. Evidência: `evidencias/10_bancada_completa_serial.txt`.

> ⚠️ **O autoteste `uiChecarLed()` deu `CIRCUITO ABERTO` com o LED montado e acendendo.**
> É falso negativo, e o limite já estava previsto: com o LED em série o pino fica em ~1,8 V,
> dentro da zona indeterminada do ESP32 (0,8–2,5 V), e o `digitalRead` com pull-up pode
> devolver 1. Essa função só detecta circuito **aberto de verdade** quando não há LED nenhum;
> com LED montado, o veredito dela não vale — só o teste visual conclui.

**Sete de oito componentes validados** (2026-08-17, `diagnostico_bancada`): OLED (0x3C),
DS18B20 (27,5 °C), pH (1938 mV), turbidez (2588 mV reais = baseline do ar), relé, buzzer.
O fio **VERMELHO (VDD) do DS18B20 havia soltado** de novo e foi recolocado.

⚠️ **Retratação (2026-08-23):** a versão anterior deste parágrafo afirmava que o LED de
status estava "confirmado aceso na varredura de saídas". Isso está **errado** — o LED nunca
acendeu, e a hipótese de "duas pernas na mesma linha" também estava errada. A causa real é
a tabela de pinos invertida acima: o GPIO13 (linha 5) está vazio, e o circuito do LED foi
montado sempre a partir da linha 33, que pertence ao buzzer. Lição de método: quando a
medição e a planta discordam por várias rodadas, **desconfiar da planta**, não continuar
remontando a peça.

**Módulo relé (validado 2026-07-09):** ativo-baixo (arma em LOW) e **alimentado em 3V3**
— com VCC em 5 V, o HIGH de 3,3 V do ESP32 não desarma o relé (fica preso armado).
Nada conectado aos bornes de carga (COM/NO/NC) nesta fase. Melhoria futura (Task 7):
dar ao relé um tap de 3V3 próprio, para o chaveamento da bobina não dividir linha com
o VDD do DS18B20.

## Rede / broker

- Mosquitto 2.1.2 em `C:\Program Files\mosquitto`, conf de teste em `ferramentas/mosquitto_teste.conf`.
- IP do PC (Ethernet): **192.168.2.2** → `MQTT_BROKER_IP`.
- Firewall: regra "Mosquitto 1883 (TCC)" criada (TCP 1883, perfil Private).

## Pendências de material

- [x] Jumpers fêmea-macho (kit 40) — chegaram em 2026-07-09; relé montado e validado
- [ ] Vedar o sensor de turbidez com cola quente/silicone — **a unidade secou e voltou a funcionar** (2588 mV no ar em 17/08, contra 2598 mV em julho); a óptica está boa, falta só vedar a emenda antes de reimergir
- [ ] Soluções tampão pH 4,01 e 6,86 + água destilada — **confirmado em 2026-07-09: os sachês NÃO vieram na caixa; comprar o par** (bloqueia só a calibração, ver `docs/calibracao_ph.md`)
- [x] Conferir pontas do cabo do sensor de pH — resolvido; cabo conectado e validado em 2026-07-09
