"""Series do historico (UC03, RNF02): leituras brutas ou agregadas em blocos de 5 min / 1 h."""

from datetime import datetime, timedelta

from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from src.db.models import Leitura, Previsao, Sensor, TipoSensor

# raw usa a cadencia do no sensor (uma leitura por minuto) para limitar a janela
PASSOS = {"raw": timedelta(minutes=1), "5m": timedelta(minutes=5), "1h": timedelta(hours=1)}
MAX_PONTOS = 5000
# date_bin e do PostgreSQL (14+), entao a consulta roda tambem no banco de teste, sem TimescaleDB.
# Intervalo e origem vao literais para o SELECT e o GROUP BY ficarem identicos
_INTERVALOS_SQL = {"5m": "interval '5 minutes'", "1h": "interval '1 hour'"}
_ORIGEM_SQL = "timestamptz '2000-01-01 00:00:00+00'"
# unidades do catalogo tipos_sensor do seed; valem enquanto o tanque nao tem sensor daquela grandeza.
# O OD nao tem sensor: e a unidade da estimativa do ML
UNIDADES_PADRAO = {"ph": "pH", "temperatura": "C", "turbidez": "NTU", "od": "mg/L"}


def _serie(sessao: Session, ts, valor, origem, filtros, bucket: str | None) -> list[dict]:
    if bucket is None:
        # sem agregacao; com mais de um no no tanque, media dos que leram no mesmo instante
        consulta = (
            select(ts, func.round(func.avg(valor), 4))
            .select_from(origem)
            .where(*filtros)
            .group_by(ts)
            .order_by(ts)
        )
        return [{"ts": t, "valor": v} for t, v in sessao.execute(consulta)]

    bloco = func.date_bin(literal_column(_INTERVALOS_SQL[bucket]), ts, literal_column(_ORIGEM_SQL))
    consulta = (
        select(bloco, func.round(func.avg(valor), 4), func.min(valor), func.max(valor))
        .select_from(origem)
        .where(*filtros)
        .group_by(bloco)
        .order_by(bloco)
    )
    return [{"ts": t, "valor": v, "min": mn, "max": mx} for t, v, mn, mx in sessao.execute(consulta)]


def serie_fisica(
    sessao: Session, id_tanque: int, grandeza: str, desde: datetime, ate: datetime, bucket: str
) -> list[dict]:
    origem = Leitura.__table__.join(Sensor, Sensor.id == Leitura.id_sensor).join(
        TipoSensor, TipoSensor.id == Sensor.id_tipo
    )
    filtros = (Sensor.id_tanque == id_tanque, TipoSensor.grandeza == grandeza, Leitura.ts.between(desde, ate))
    return _serie(sessao, Leitura.ts, Leitura.valor, origem, filtros, None if bucket == "raw" else bucket)


def serie_od(sessao: Session, id_tanque: int, desde: datetime, ate: datetime, bucket: str) -> list[dict]:
    # OD estimado: linhas h = 0 do servico de ML, uma por ciclo (5 min); so o bucket de 1 h agrega
    filtros = (
        Previsao.id_tanque == id_tanque,
        Previsao.horizonte_h == 0,
        Previsao.ts_previsao.between(desde, ate),
    )
    return _serie(
        sessao, Previsao.ts_previsao, Previsao.valor_previsto, Previsao.__table__, filtros,
        "1h" if bucket == "1h" else None,
    )


def unidades_do_tanque(sessao: Session, id_tanque: int) -> dict[str, str]:
    linhas = sessao.execute(
        select(TipoSensor.grandeza, TipoSensor.unidade)
        .join(Sensor, Sensor.id_tipo == TipoSensor.id)
        .where(Sensor.id_tanque == id_tanque)
        .distinct()
    ).all()
    return UNIDADES_PADRAO | {grandeza: unidade for grandeza, unidade in linhas}
