from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import Connection, text

from src.faixas import FaixaEspecie
from src.features import BLOCO, para_grade_15min

MINUTOS_JANELA = 90
BLOCOS_JANELA = MINUTOS_JANELA // 15
GRANDEZAS_ENTRADA = ["ph", "temperatura"]

SQL_TANQUES_ATIVOS = text(
    """
    SELECT t.id, e.ph_min, e.ph_max, e.temp_min, e.temp_max, e.od_min, e.od_max
    FROM tanques t
    JOIN especies e ON e.id = t.id_especie
    WHERE t.status = 'ativo'
    ORDER BY t.id
    """
)

SQL_LEITURAS = text(
    """
    SELECT l.ts, tp.grandeza, l.valor
    FROM leituras l
    JOIN sensores s ON s.id = l.id_sensor
    JOIN tipos_sensor tp ON tp.id = s.id_tipo
    WHERE s.id_tanque = :id_tanque
      AND s.status = 'ativo'
      AND tp.grandeza IN ('ph', 'temperatura')
      AND l.ts >= :desde AND l.ts <= :ate
    """
)


def tanques_ativos(conn: Connection) -> list[tuple[int, FaixaEspecie]]:
    """Tanques ativos com a faixa da espécie; tanque sem espécie fica de fora (não há faixa)."""
    return [
        (linha.id, FaixaEspecie(*(float(v) for v in linha[1:])))
        for linha in conn.execute(SQL_TANQUES_ATIVOS)
    ]


def ler_janela(conn: Connection, id_tanque: int, agora: datetime, recentes_min: int = 0) -> pd.DataFrame:
    """Últimos 90 min de pH e temperatura em 6 blocos de 15 min; o último é o bloco de `agora` (pode estar parcial).

    Com `recentes_min` > 0 (modo demonstração), o bloco de `agora` usa só a mediana dos últimos
    `recentes_min` minutos, para a previsão acompanhar uma troca de copo sem esperar o bloco fechar.
    """
    grade = pd.date_range(end=pd.Timestamp(agora).floor(BLOCO), periods=BLOCOS_JANELA, freq=BLOCO)
    linhas = conn.execute(SQL_LEITURAS, {"id_tanque": id_tanque, "desde": grade[0], "ate": agora}).all()
    if not linhas:
        return pd.DataFrame(index=grade, columns=GRANDEZAS_ENTRADA, dtype=float)

    bruto = pd.DataFrame(linhas, columns=["ts", "grandeza", "valor"])
    bruto["valor"] = bruto["valor"].astype(float)
    bruto["ts"] = pd.to_datetime(bruto["ts"], utc=True)
    largo = (
        bruto.pivot_table(index="ts", columns="grandeza", values="valor", aggfunc="median")
        .reindex(columns=GRANDEZAS_ENTRADA)
        .reset_index()
    )
    janela = para_grade_15min(largo, GRANDEZAS_ENTRADA).reindex(grade)
    if recentes_min > 0:
        recentes = bruto[bruto["ts"] > pd.Timestamp(agora) - timedelta(minutes=recentes_min)]
        for grandeza, valores in recentes.groupby("grandeza")["valor"]:
            janela.loc[grade[-1], grandeza] = valores.median()
    return janela
