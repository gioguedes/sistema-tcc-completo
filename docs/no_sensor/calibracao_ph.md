# Calibração do sensor de pH (SEN0161-V2)

**Status: CALIBRADO em 26/10/2026** (2 pontos, tampões 4,01 e 6,86).

A fiação e a leitura de tensão já tinham sido validadas em 2026-07-09
(ver `docs/evidencias/05_ph_serial.txt`).

## Procedimento usado

Não foi preciso gravar o `teste_ph`: com o firmware do nó gravado, o script
`TCC\implementacao\calibracao\ler_ph.ps1` envia o comando `ler` pela serial e
converte o pH publicado de volta em tensão, invertendo a reta das constantes
vigentes na placa (resolução de ~1,9 mV, pois o pH sai com 2 casas).

1. Enxaguar o eletrodo na água destilada (sem esfregar o bulbo);
2. Mergulhar no tampão **4,01** e ler em rodadas de 6 a 14 leituras (~5 s cada)
   até a média parar de andar;
3. Enxaguar de novo e repetir no tampão **6,86**;
4. Passar as médias para `PH_CAL_MV1`/`PH_CAL_MV2` no `config.h` com
   `PH_CALIBRADO 1`, compilar e gravar;
5. Devolver o eletrodo à garrafinha de armazenamento.

## Registro da calibração

| Item | Valor |
|---|---|
| Data | 26/10/2026 |
| Tensão no tampão 4,01 (`PH_CAL_MV1`) | 2077 mV |
| Tensão no tampão 6,86 (`PH_CAL_MV2`) | 1614 mV |
| Inclinação | 162,5 mV/pH (~92% dos 177,5 mV/pH implícitos nos valores padrão da biblioteca DFRobot: 1500 mV em pH 7,0 e 2032,44 mV em pH 4,0) |
| Temperatura | não anotada (ambiente da bancada, ~21 °C pelo DS18B20 no início do teste de deriva) |

Constantes resultantes: `PH_CAL_PH1 = 4.01`, `PH_CAL_MV1 = 2077`,
`PH_CAL_PH2 = 6.86`, `PH_CAL_MV2 = 1614`.

### Leituras (médias por rodada, em mV)

- **Tampão 4,01**: 2059,8 → 2064,7 → 2073,6 → 2077,2. O eletrodo saiu da
  solução de armazenamento e levou ~5 min para estabilizar (deriva caindo de
  ~6 para ~1 mV/min). Valor adotado: média da última rodada, cuja metade final
  coincidia com a anterior. Ruído entre leituras: ±8 mV (±0,05 pH).
- **Tampão 6,86**: 1615,5 → 1612,3, estável desde a primeira rodada. Valor
  adotado: média das duas, 1614 mV.

Na garrafinha de armazenamento, antes da calibração, o eletrodo lia ~1901 mV.

### Conferência com o firmware calibrado gravado

| Tampão | pH medido (média) | Erro |
|---|---|---|
| 6,86 | 6,89 (10 leituras, 6,87–6,91) | +0,03 |
| 4,01 | 4,03 (14 leituras, 4,00–4,07, após ~2 min no tampão) | +0,02 |
