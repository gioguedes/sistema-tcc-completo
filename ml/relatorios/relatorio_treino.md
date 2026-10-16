# Relatório de treino: estimador de OD e classificador de risco

Gerado em: 2026-10-16T00:01:47.214479+00:00

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
| xgboost | 0.595 | 0.757 | 0.767 | 95.6% |
| random_forest | 0.621 | 0.784 | 0.751 | 94.9% |
| mediana | 1.345 | 1.588 | -0.023 | 95.6% |

H1: **ATINGIDA**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | MAE XGBoost | MAE Random Forest | MAE mediana |
|---|---|---|---|
| lake_houston | 1.442 | 1.419 | 1.911 |
| luce_bayou | 0.954 | 0.962 | 1.623 |
| st_lucie | 1.517 | 1.537 | 1.896 |
| winona | 0.604 | 0.677 | 1.754 |
| **média** | 1.129 | 1.149 | 1.796 |

Split temporal (2023 → 2024, corpos de treino):

| Modelo | MAE (mg/L) | RMSE | R² | Acurácia de faixa |
|---|---|---|---|---|
| xgboost | 1.104 | 1.515 | 0.498 | 88.0% |
| random_forest | 1.121 | 1.509 | 0.501 | 88.5% |
| mediana | 1.617 | 2.146 | -0.009 | 90.2% |

## Classificador de risco (H2: acurácia ≥ 80% pelo TC1; a spec exige também recall de crítico acima da persistência)

### Horizonte 1 h

Teste final:

Distribuição ótimo/atenção/crítico: [21520, 7534, 31103]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost | 96.3% | 0.941 | 96.7% | [[20945, 512, 63], [196, 6876, 462], [135, 886, 30082]] |
| random_forest | 96.6% | 0.946 | 96.5% | [[21260, 259, 1], [292, 6817, 425], [176, 916, 30011]] |
| persistencia | 97.8% | 0.964 | 98.2% | [[21299, 220, 1], [325, 6956, 253], [181, 364, 30558]] |

H2 neste horizonte, critério do TC1 (acurácia ≥ 80%): **ATINGIDA** | critério da spec (também ganhar da persistência no recall de crítico): **NÃO atingida**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | Acurácia XGBoost | Recall crítico XGBoost | Acurácia RF | Acurácia persistência | Recall crítico persistência |
|---|---|---|---|---|---|
| lake_houston | 86.3% | 96.4% | 85.8% | 85.5% | 96.9% |
| luce_bayou | 96.3% | 96.3% | 96.2% | 97.4% | 98.8% |
| st_lucie | 87.2% | 76.0% | 87.2% | 88.5% | 79.9% |
| winona | 66.9% | 67.7% | 45.4% | 99.2% | 99.9% |
| **média** | 84.2% | 84.1% | 78.7% | 92.7% | 93.9% |

Split temporal (2023 → 2024, corpos de treino):

Distribuição ótimo/atenção/crítico: [49455, 19641, 94172]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost | 90.2% | 0.856 | 92.3% | [[45704, 1808, 1943], [2897, 14549, 2195], [3232, 3985, 86955]] |
| random_forest | 90.8% | 0.857 | 92.0% | [[48075, 1298, 82], [3354, 13606, 2681], [3523, 4034, 86615]] |
| persistencia | 86.2% | 0.818 | 93.4% | [[38685, 2205, 8565], [1645, 14109, 3887], [2535, 3689, 87948]] |

### Horizonte 2 h

Teste final:

Distribuição ótimo/atenção/crítico: [21513, 7534, 31034]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost | 95.1% | 0.925 | 95.1% | [[20551, 830, 132], [221, 7036, 277], [115, 1398, 29521]] |
| random_forest | 94.8% | 0.921 | 94.5% | [[20782, 731, 0], [255, 6864, 415], [154, 1541, 29339]] |
| persistencia | 96.8% | 0.947 | 97.7% | [[21154, 359, 0], [473, 6649, 412], [172, 527, 30335]] |

H2 neste horizonte, critério do TC1 (acurácia ≥ 80%): **ATINGIDA** | critério da spec (também ganhar da persistência no recall de crítico): **NÃO atingida**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | Acurácia XGBoost | Recall crítico XGBoost | Acurácia RF | Acurácia persistência | Recall crítico persistência |
|---|---|---|---|---|---|
| lake_houston | 83.6% | 94.9% | 82.0% | 83.6% | 95.9% |
| luce_bayou | 94.4% | 95.0% | 94.2% | 95.2% | 97.9% |
| st_lucie | 85.0% | 72.3% | 84.9% | 86.7% | 78.7% |
| winona | 47.7% | 47.2% | 41.3% | 98.7% | 99.7% |
| **média** | 77.7% | 77.4% | 75.6% | 91.1% | 93.1% |

Split temporal (2023 → 2024, corpos de treino):

Distribuição ótimo/atenção/crítico: [49438, 19625, 93936]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost | 88.2% | 0.817 | 91.2% | [[45651, 2289, 1498], [3371, 12393, 3861], [2868, 5394, 85674]] |
| random_forest | 88.3% | 0.811 | 90.3% | [[47465, 1838, 135], [5583, 11614, 2428], [3688, 5413, 84835]] |
| persistencia | 84.5% | 0.790 | 92.5% | [[38090, 2730, 8618], [2087, 12849, 4689], [2663, 4402, 86871]] |

### Horizonte 3 h

Teste final:

Distribuição ótimo/atenção/crítico: [21509, 7532, 30970]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost | 93.8% | 0.909 | 92.8% | [[20375, 1036, 98], [277, 7174, 81], [117, 2104, 28749]] |
| random_forest | 93.2% | 0.898 | 92.2% | [[20592, 916, 1], [333, 6762, 437], [128, 2282, 28560]] |
| persistencia | 95.8% | 0.929 | 97.3% | [[21005, 501, 3], [634, 6336, 562], [156, 694, 30120]] |

H2 neste horizonte, critério do TC1 (acurácia ≥ 80%): **ATINGIDA** | critério da spec (também ganhar da persistência no recall de crítico): **NÃO atingida**

Validação cruzada por corpo d'água (treino):

| Corpo d'água fora | Acurácia XGBoost | Recall crítico XGBoost | Acurácia RF | Acurácia persistência | Recall crítico persistência |
|---|---|---|---|---|---|
| lake_houston | 79.7% | 93.5% | 78.0% | 82.1% | 95.2% |
| luce_bayou | 92.4% | 93.2% | 92.2% | 93.2% | 97.0% |
| st_lucie | 82.9% | 69.3% | 82.5% | 85.0% | 77.5% |
| winona | 44.7% | 44.7% | 34.8% | 98.3% | 99.6% |
| **média** | 74.9% | 75.2% | 71.9% | 89.7% | 92.3% |

Split temporal (2023 → 2024, corpos de treino):

Distribuição ótimo/atenção/crítico: [49420, 19625, 93738]

| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |
|---|---|---|---|---|
| xgboost | 86.1% | 0.784 | 89.4% | [[44835, 3641, 944], [4288, 11491, 3846], [2780, 7191, 83767]] |
| random_forest | 86.4% | 0.788 | 88.4% | [[46672, 2347, 401], [4895, 11146, 3584], [3905, 6963, 82870]] |
| persistencia | 83.2% | 0.768 | 91.8% | [[37552, 3179, 8689], [2435, 11890, 5300], [2827, 4900, 86011]] |

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
