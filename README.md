# Sistema Inteligente de Monitoramento da Qualidade da Água em Tanques de Piscicultura

TCC de Ciência da Computação (UNIP, 2026). Um nó sensor (ESP32) mede pH, temperatura e turbidez
de um tanque e publica por MQTT. O backend grava as leituras num banco de séries temporais. O
serviço de Machine Learning estima o oxigênio dissolvido (OD), que não tem sensor, e prevê o
nível de risco para 1, 2 e 3 horas. O painel web (PWA) mostra tudo e comanda o aerador.

```
nó ESP32 ──MQTT QoS 1──► broker ──► ingestão (backend/src/mqtt) ──► TimescaleDB
   ▲                                                                  │
   └──── comando do aerador (MQTT retido) ◄── API (backend/src/api) ◄─┤
                                                 ▲                     │
                                  painel (dashboard/) ◄────────────────┤
                                                                       ▼
                                          serviço de ML (ml/): OD estimado + risco 1–3 h
```

## Pastas

| Pasta | O que tem | Detalhes |
|---|---|---|
| `backend/` | Ingestão MQTT, modelos do banco (SQLAlchemy + Alembic), API FastAPI com JWT, comando do aerador | [`backend/API.md`](backend/API.md) |
| `ml/` | Download dos dados do USGS, treino, relatório e serviço periódico de previsão | [`ml/relatorios/relatorio_treino.md`](ml/relatorios/relatorio_treino.md) |
| `dashboard/` | Painel React (PWA), com modo simulado (MSW) ou ligado à API real | [`dashboard/README.md`](dashboard/README.md) |
| `docs/evidencias/` | Evidências dos casos de teste (CT02 ponta a ponta) | |

O firmware do nó sensor e o modelo 3D da caixa ficam num repositório separado.

## Como rodar

Pré-requisitos: Python 3.13, Node.js 22.12+, Docker Desktop.

```bash
# 1. banco (TimescaleDB) e broker MQTT de teste, ambos só em 127.0.0.1
cd backend
cp .env.example .env            # preencher DB_USER, DB_PASSWORD e API_JWT_SEGREDO
docker compose up -d timescaledb mosquitto-test
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m alembic upgrade head

# 2. ingestão (assina <prefixo>/+/leituras) e API (porta 8000)
.venv/Scripts/python -m src.main
.venv/Scripts/python -m src.api

# 3. serviço de ML (ciclo de 5 min); o pacote de modelos sai do treino
cd ../ml
cp .env.example .env            # mesmas credenciais do banco; ML_ALTITUDE_M = altitude do tanque
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m src.dados.baixar_usgs   # dados públicos do USGS (~555 mil linhas)
.venv/Scripts/python -m src.treino              # grava ml/modelos/modelos.joblib e o relatório
.venv/Scripts/python -m src.servico

# 4. painel (http://localhost:5173)
cd ../dashboard
npm install && npm run dev      # modo simulado; para a API real, ver dashboard/README.md
```

Sem o nó físico, `backend/scripts/simular_leituras.py` publica leituras no mesmo formato do firmware.

## Testes

```bash
cd backend && .venv/Scripts/python -m pytest      # 110 testes (precisam do banco e do mosquitto-test)
cd ml && .venv/Scripts/python -m pytest           # 124 testes (criam o banco piscicultura_ml_test)
cd dashboard && npm test                          # 41 testes
```

## Machine Learning em resumo

- **Dados de treino:** 5 corpos d'água do USGS com leituras a cada 15 min (só as aprovadas),
  agregadas em blocos de 15 min. O teste final é um corpo d'água inteiro que o treino não vê
  (`lynchburg`). Também há validação cruzada por corpo d'água e um split temporal (2023 → 2024).
- **Estimador de OD:** XGBoost em temperatura e pH que estima a fração de saturação do oxigênio,
  com restrição monotônica, e converte para mg/L pela altitude do tanque. Fora do intervalo de
  pH e temperatura do treino, a confiança vai a 0.
- **Previsão de risco:** XGBoost prevê o pH e a temperatura em 1, 2 e 3 h, e o nível sai da
  mesma regra de faixas da espécie (tilápia), com o OD estimado a partir dos valores previstos.
- **Resultados** (detalhes em `ml/relatorios/relatorio_treino.md`):
  - OD: MAE de 0,515 mg/L no teste final e 1,079 na validação cruzada.
  - Risco: acurácia de 97,3%, 96,6% e 95,7% em 1, 2 e 3 h no teste final, com recall de
    crítico acima da persistência.
  - A previsão só agrega à persistência nas mudanças de nível; o relatório mostra as duas lado a lado.

## Limitações conhecidas

- O broker MQTT é público e sem autenticação. A ingestão descarta leituras cujo MAC do payload
  não bate com o do tópico, mas isso não substitui autenticação.
- O OD é estimado por um modelo treinado em lagos dos EUA. No tanque, ele é uma indicação e
  precisa de medições de referência.
- O nó ainda não confirma o estado do relé do aerador; o painel mostra o último comando enviado.
