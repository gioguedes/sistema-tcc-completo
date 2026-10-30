# Relatório de treino: estimador de OD e previsão de risco

Gerado em: 2026-10-30T01:13:25.596005+00:00

## Dados (USGS, só leituras aprovadas, blocos de 15 min)

| Corpo d'água | Pontos | Blocos válidos |
|---|---|---|
| st_lucie | 02276998 | 70060 |
| winona | 073625897 | 41793 |
| luce_bayou | 08066850 | 42289 |
| lynchburg | 294643095035200 | 60429 |
| lake_houston | 295554095093402, 295826095082200, 300032095080501 | 154283 |

Teste final (CT04): ['lynchburg'] (16.4% dos blocos). Treino: ['lake_houston', 'luce_bayou', 'st_lucie', 'winona'].

Níveis pela faixa da tilápia em todos os blocos: ótimo 29.1%, atenção 11.5%, crítico 59.4%.

## Limpeza (linhas removidas por regra)

- nao_aprovado: 10255
- temperatura: 105633
- ph: 0
- od_faixa: 2
- linhas brutas: 555256 | após limpeza: 439366

## Estimador de OD (H1: MAE ≤ 0,8 mg/L no teste final)

Teste final:

| Modelo | MAE (mg/L) | RMSE | R² | Acurácia de faixa |
|---|---|---|---|---|
| xgboost | 0.515 | 0.645 | 0.831 | 95.6% |
| random_forest | 0.621 | 0.784 | 0.751 | 94.9% |
| mediana | 1.345 | 1.588 | -0.023 | 95.6% |

H1: **ATINGIDA**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | MAE XGBoost | MAE Random Forest | MAE mediana |
|---|---|---|---|
| lake_houston | 1.246 | 1.419 | 1.911 |
| luce_bayou | 0.819 | 0.962 | 1.623 |
| st_lucie | 1.470 | 1.537 | 1.896 |
| winona | 0.780 | 0.677 | 1.754 |
| **média** | 1.079 | 1.149 | 1.796 |

Split temporal (2023 → 2024, corpos de treino):

| Modelo | MAE (mg/L) | RMSE | R² | Acurácia de faixa |
|---|---|---|---|---|
| xgboost | 1.037 | 1.424 | 0.556 | 89.1% |
| random_forest | 1.121 | 1.509 | 0.501 | 88.5% |
| mediana | 1.617 | 2.146 | -0.009 | 90.2% |

## Previsão de risco (H2: acurácia ≥ 80% pelo TC1; a spec exige também recall de crítico acima da persistência)

O XGBoost prevê a variação de pH e de temperatura até t+h; o OD em t+h sai do estimador de OD aplicado a esses valores, e o nível sai da mesma regra de faixas do rótulo. O classificador direto do nível (modelo de risco até 29/10/2026) fica como linha de base.

### Horizonte 1 h

Teste final:

Distribuição ótimo/atenção/crítico: [21520, 7534, 31103]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost (previsão de pH e T + regra) | 97.3% | 0.956 | 98.6% | [[21040, 479, 1], [223, 6833, 478], [177, 271, 30655]] |
| classificador direto (linha de base) | 96.9% | 0.952 | 96.6% | [[21138, 381, 1], [263, 7108, 163], [183, 868, 30052]] |
| persistência | 97.8% | 0.964 | 98.2% | [[21299, 220, 1], [325, 6956, 253], [181, 364, 30558]] |

H2 neste horizonte, critério do TC1 (acurácia ≥ 80%): **ATINGIDA** | critério da spec (também ganhar da persistência no recall de crítico): **ATINGIDA**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | Acurácia XGBoost | Recall crítico XGBoost | Acurácia classificador | Acurácia persistência | Recall crítico persistência |
|---|---|---|---|---|---|
| lake_houston | 87.2% | 97.9% | 86.4% | 88.1% | 97.5% |
| luce_bayou | 96.8% | 99.6% | 96.2% | 97.4% | 98.8% |
| st_lucie | 88.3% | 81.3% | 87.1% | 88.5% | 79.9% |
| winona | 98.7% | 99.5% | 55.3% | 99.2% | 99.9% |
| **média** | 92.8% | 94.6% | 81.2% | 93.3% | 94.0% |

Split temporal (2023 → 2024, corpos de treino):

Distribuição ótimo/atenção/crítico: [49455, 19641, 94172]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost (previsão de pH e T + regra) | 91.3% | 0.864 | 95.9% | [[45453, 2552, 1450], [1599, 13371, 4671], [2716, 1138, 90318]] |
| classificador direto (linha de base) | 89.9% | 0.845 | 93.0% | [[45845, 1804, 1806], [2116, 13275, 4250], [2386, 4178, 87608]] |
| persistência | 88.1% | 0.827 | 94.0% | [[41210, 4323, 3922], [1564, 14053, 4024], [2526, 3139, 88507]] |

### Horizonte 2 h

Teste final:

Distribuição ótimo/atenção/crítico: [21513, 7534, 31034]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost (previsão de pH e T + regra) | 96.6% | 0.944 | 98.2% | [[20940, 573, 0], [330, 6605, 599], [164, 397, 30473]] |
| classificador direto (linha de base) | 95.7% | 0.934 | 95.1% | [[20938, 575, 0], [370, 7058, 106], [195, 1326, 29513]] |
| persistência | 96.8% | 0.947 | 97.7% | [[21154, 359, 0], [473, 6649, 412], [172, 527, 30335]] |

H2 neste horizonte, critério do TC1 (acurácia ≥ 80%): **ATINGIDA** | critério da spec (também ganhar da persistência no recall de crítico): **ATINGIDA**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | Acurácia XGBoost | Recall crítico XGBoost | Acurácia classificador | Acurácia persistência | Recall crítico persistência |
|---|---|---|---|---|---|
| lake_houston | 84.8% | 96.9% | 84.0% | 86.2% | 96.5% |
| luce_bayou | 95.6% | 99.0% | 94.2% | 95.2% | 97.9% |
| st_lucie | 87.0% | 80.7% | 85.1% | 86.7% | 78.7% |
| winona | 98.1% | 99.1% | 48.6% | 98.7% | 99.8% |
| **média** | 91.4% | 93.9% | 78.0% | 91.7% | 93.2% |

Split temporal (2023 → 2024, corpos de treino):

Distribuição ótimo/atenção/crítico: [49438, 19625, 93936]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost (previsão de pH e T + regra) | 90.5% | 0.846 | 94.9% | [[45688, 2706, 1044], [2323, 12577, 4725], [2858, 1903, 89175]] |
| classificador direto (linha de base) | 87.9% | 0.819 | 91.7% | [[44374, 2104, 2960], [2958, 12793, 3874], [2613, 5212, 86111]] |
| persistência | 86.4% | 0.800 | 93.1% | [[40623, 4828, 3987], [1996, 12806, 4823], [2654, 3857, 87425]] |

### Horizonte 3 h

Teste final:

Distribuição ótimo/atenção/crítico: [21509, 7532, 30970]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost (previsão de pH e T + regra) | 95.7% | 0.929 | 97.6% | [[20784, 724, 1], [405, 6411, 716], [148, 604, 30218]] |
| classificador direto (linha de base) | 94.3% | 0.914 | 93.1% | [[20716, 792, 1], [398, 7036, 98], [164, 1973, 28833]] |
| persistência | 95.8% | 0.929 | 97.3% | [[21005, 501, 3], [634, 6336, 562], [156, 694, 30120]] |

H2 neste horizonte, critério do TC1 (acurácia ≥ 80%): **ATINGIDA** | critério da spec (também ganhar da persistência no recall de crítico): **ATINGIDA**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | Acurácia XGBoost | Recall crítico XGBoost | Acurácia classificador | Acurácia persistência | Recall crítico persistência |
|---|---|---|---|---|---|
| lake_houston | 83.7% | 95.7% | 79.0% | 84.7% | 95.7% |
| luce_bayou | 94.1% | 98.2% | 92.4% | 93.2% | 97.0% |
| st_lucie | 86.0% | 80.3% | 82.6% | 85.0% | 77.5% |
| winona | 98.0% | 99.5% | 45.5% | 98.3% | 99.7% |
| **média** | 90.5% | 93.4% | 74.9% | 90.3% | 92.5% |

Split temporal (2023 → 2024, corpos de treino):

Distribuição ótimo/atenção/crítico: [49420, 19625, 93738]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost (previsão de pH e T + regra) | 89.0% | 0.821 | 94.3% | [[45052, 3084, 1284], [2714, 11484, 5427], [3000, 2361, 88377]] |
| classificador direto (linha de base) | 86.5% | 0.792 | 89.4% | [[45213, 3352, 855], [3589, 11815, 4221], [2873, 7065, 83800]] |
| persistência | 85.1% | 0.779 | 92.3% | [[40103, 5251, 4066], [2332, 11850, 5443], [2814, 4376, 86548]] |

## Domínio do estimador de OD (percentis 1 e 99 do treino)

- temperatura: 15.20 a 33.50
- ph: 5.90 a 9.40

Fora desse domínio o serviço grava o OD com confiança 0 (o modelo nunca viu esses valores).

## Datasets (SHA-256)

- `295826095082200/2023-01.rdb`: `26764a8a7f56189da07889bd76e97ccb1d96582ca5e4a32fdec79729e99e8ec1`
- `295826095082200/2023-04.rdb`: `53817e3e7e4e362b1c4d2c0268a98505b815335ec86f84633f0e7721d93ef24d`
- `295826095082200/2023-07.rdb`: `4be9aacb57909f90ca2b1cb9a8fc07e76150e75ee3a2d26aa593d89692de67ff`
- `295826095082200/2023-10.rdb`: `2ca59f89493f5f91d9ba0448068c0d21385b429fd2b4c9b266931df437fc9d3e`
- `295826095082200/2024-01.rdb`: `e32985f0d515318e5aa36e4e2fa01d77796896ad19461d88e5ae2626496c2048`
- `295826095082200/2024-04.rdb`: `03714a5b52f20b9d1842dc2d9d90faf43d60eb60b9758ed062fa5f983cb82e0e`
- `295826095082200/2024-07.rdb`: `29672e0431ae207c5425428ee65121421559be1f8038447c11fd3f3e210b1358`
- `295826095082200/2024-10.rdb`: `3e18c09d7d469f5d4818323d0f791dcd165474a8a7e536bc47daf29bce83901f`
- `295554095093402/2023-01.rdb`: `84aa78587c19088e8a4186c10854317875eb256e5f892da7c8f17a8968dd9f8b`
- `295554095093402/2023-04.rdb`: `a20856055d766ebf22e7abf33c9635d17e2603769fcb9bb6fc23a85985d2812a`
- `295554095093402/2023-07.rdb`: `b314b13dbdb0731c7fc57578202f72898bbf96b8085d4a78a8b534e34642c9b5`
- `295554095093402/2023-10.rdb`: `1fc6a340db69b0fb4027635248b13962e63a07f2a717f631f815bc87c928f84a`
- `295554095093402/2024-01.rdb`: `1696b5d63d8e51b7a83da065aa40db3037a1fc1aa88747837e638ca1b25425b5`
- `295554095093402/2024-04.rdb`: `c3227b554c3d5753571acf52573cd305cefdd7f9169571c14ec4e3fe949667e6`
- `295554095093402/2024-07.rdb`: `73c5138ac662cfab5b66c1805fdac8139069a4e9605910f5ab2c866f095d03e9`
- `295554095093402/2024-10.rdb`: `222a00cf31adc490af4fdaa95442571ca5d61b9c3dafed207a721cb88264b95c`
- `300032095080501/2023-01.rdb`: `a75a6fda3335f717597e0ca00674f07be929ba8c1571f20d04dd4e96d23e6158`
- `300032095080501/2023-04.rdb`: `bcfe5df3be058b0a14dee03ebdadd2be37889d76a6ff0516feebcf3dc1392c29`
- `300032095080501/2023-07.rdb`: `49643d1875f1d9eab48296dc33086b76dcf1b2fdc98592c61dfc5da7c0b5f3f6`
- `300032095080501/2023-10.rdb`: `3c4b15851915685514411be7f679604db302950ee2a7d92ee859a37a575976d5`
- `300032095080501/2024-01.rdb`: `9a5fd7c475d68a3145d5ae3a0cf87367d109155129d107d24c53afbce9708d37`
- `300032095080501/2024-04.rdb`: `c4fb3d19a0298b22e64450484e1fc5166256ade07310ad70d48f32e2d46c4f0c`
- `300032095080501/2024-07.rdb`: `f26db2d57bb689da0655818f9fb390c001bf6a71fd659d0aec048c39c4d62a9b`
- `300032095080501/2024-10.rdb`: `d5c39d67a99e4fb0f34896363269235592b12ace2782c9287f700ffb78cceff9`
- `294643095035200/2023-01.rdb`: `eca187d4bd9fff7443338656cd6a798049b3b46dc11a3d8d4babfdfd41255e4e`
- `294643095035200/2023-04.rdb`: `924bf0efd7c644dda611aee2668e272e714364877463edf21980172e50cbab9f`
- `294643095035200/2023-07.rdb`: `718ffa49cd8e632ca804eb9d86ff59723e4cb1f72e76efd42eadc979c2227e5a`
- `294643095035200/2023-10.rdb`: `5adacce2c57c0f28d364e5b5ed68a14db495531ecd3e32ab203ce7a6d813ce29`
- `294643095035200/2024-01.rdb`: `9cf4597f24966ab9cb25e6f2f6fb6ac1c29302980dbb39b9b6a9e13194d6ad44`
- `294643095035200/2024-04.rdb`: `99173b98fa470c47c1543e7ac86802387a776188329d1f97e90c40b46b374585`
- `294643095035200/2024-07.rdb`: `c7ebe9fe205fcf0545df1dcfd24e6c488642dea9e5cd23e26258f071acfb3856`
- `294643095035200/2024-10.rdb`: `bdda7cbf2ee77847a41049bd821cef58442dcfc0232c17f705c99a4f5652c9b3`
- `08066850/2023-01.rdb`: `882bf8d5e4df1f451c9d6309ad86d16c256552b7a8b9cb17024d861397536368`
- `08066850/2023-04.rdb`: `4fbfb8f54f2eec2381f6fcacd5437b4b21cf30e1121ffa062727345d915f11c6`
- `08066850/2023-07.rdb`: `59d80c9be57a938a3169bce4f73429d5ed18cda76e40f00d5b72c9869ff6f6a8`
- `08066850/2023-10.rdb`: `7cb9cac5a560f0451a81c124a12ddb8d5e6c06addbf5644a5a604ae7ec8c7e5c`
- `08066850/2024-01.rdb`: `62c794816efdcb245f986c69e431d5c3c1ef7a489a82547ca53d3bb71ba6c2e6`
- `08066850/2024-04.rdb`: `4bea668e6b82561f04f56f60ffdc91331c3b2b479119f9ef180fea160b4986e9`
- `08066850/2024-07.rdb`: `7c5ad124868dd68b1ea6bb49b157066767ddaa92d68c83fcc7a844dd98846d2d`
- `08066850/2024-10.rdb`: `7337e379d6bf759bece1049f2382aa3a5eff41187f9c02da01510d65f3837917`
- `02276998/2023-01.rdb`: `d49fb61a39eb3020e3c7f7f3684afcf8fd3000c1e84d2a3a7c5f3a31c0369934`
- `02276998/2023-04.rdb`: `fc02ad8300d7df026e138305497fcc28dde53219aa370b454670dd28a1ebb6bb`
- `02276998/2023-07.rdb`: `eb492e42f63c305355debcccacb368b1edb8df474ed810bf15757cb0d4e6adf7`
- `02276998/2023-10.rdb`: `bfa59231273a34e1b74ed914981f061e9170c67c0662e61d98ee6fa68d9abb5e`
- `02276998/2024-01.rdb`: `db706dd7fd2517961f5699e330981b633a2c5970509114b112be6a918529954c`
- `02276998/2024-04.rdb`: `416e9200d58c0167729e61a86a8ac628cd2bcc43d2d3bae9bc708cf936456f88`
- `02276998/2024-07.rdb`: `39986fffb18efdd67c4b1c147055a09dfdbe78f9818ac3c31f0590e3ee126358`
- `02276998/2024-10.rdb`: `286ba0a42ecb292710cc5c75b86115bc176757f5ab289b53b38d6add80f88fcb`
- `073625897/2023-01.rdb`: `52a712fef3f0eef6c63973d0ae139984dc1a95962fce4a06546acdd207041280`
- `073625897/2023-04.rdb`: `0567de69f526e9b5d37d7269080e4042b670cfeaa95b2dd33e355a38250845ae`
- `073625897/2023-07.rdb`: `0334ece11960f8afbafda267748f3cbeecd053d22e37702ecbf9f9d3db8d76c8`
- `073625897/2023-10.rdb`: `2dd7376f52770fbf676c26048158f7d0e88390e5720965362d670675dff3acd1`
- `073625897/2024-01.rdb`: `77bbb0b13cb94bed2b717ce139d32176efaff880129746802f8a0192590295f4`
- `073625897/2024-04.rdb`: `f3f476202b13817590251b7d05354156e487a4568a6ec0ceb35bacbea5e552ab`
- `073625897/2024-07.rdb`: `1301d3131253672194ac871b3f2b77810c7c4226502429a5cae773eb529db4ea`
- `073625897/2024-10.rdb`: `709d1be53aa1757687f29aea9f5a4ce3aa9873efd53bbadb2eb4ba167cbb0153`
