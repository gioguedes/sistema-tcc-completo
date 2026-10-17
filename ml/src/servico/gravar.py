from datetime import datetime

from sqlalchemy import Connection, text

from src.servico.inferencia import Previsao

SQL_INSERIR = text(
    """
    INSERT INTO previsoes
        (id_tanque, parametro_critico, valor_previsto, nivel_risco, horizonte_h, confianca, ts_previsao)
    VALUES
        (:id_tanque, :parametro_critico, :valor_previsto, :nivel_risco, :horizonte_h, :confianca, :ts_previsao)
    """
)


def gravar_previsoes(conn: Connection, id_tanque: int, previsoes: list[Previsao], ts_previsao: datetime) -> int:
    conn.execute(
        SQL_INSERIR,
        [
            {
                "id_tanque": id_tanque,
                "parametro_critico": p.parametro_critico,
                "valor_previsto": round(p.valor_previsto, 4),
                "nivel_risco": p.nivel_risco,
                "horizonte_h": p.horizonte_h,
                "confianca": round(p.confianca, 4),
                "ts_previsao": ts_previsao,
            }
            for p in previsoes
        ],
    )
    return len(previsoes)
