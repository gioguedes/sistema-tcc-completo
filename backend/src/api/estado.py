"""Situacao atual de cada tanque, calculada de `leituras` (ingestao) e `previsoes` (servico de ML)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from src.api import faixas
from src.db.models import Especie, Leitura, Previsao, Sensor, Tanque, TipoSensor

# sem leitura ha mais de 5 min o no conta como offline (fluxo alternativo do UC02);
# a ingestao nao atualiza dispositivos.status_conexao nem ultimo_heartbeat
LIMITE_OFFLINE = timedelta(minutes=5)
# 3 ciclos do servico de ML (ML_INTERVALO_S = 300): depois disso a previsao nao vale mais
LIMITE_PREVISAO = timedelta(minutes=15)
GRANDEZAS_FISICAS = ("ph", "temperatura", "turbidez")


@dataclass(frozen=True)
class UltimaLeitura:
    id_tanque: int
    id_dispositivo: int
    grandeza: str
    valor: Decimal
    unidade: str
    ts: datetime


@dataclass(frozen=True)
class SituacaoTanque:
    leituras: dict[str, UltimaLeitura]
    ultima_por_dispositivo: dict[int, datetime]
    # linhas do ultimo ciclo do ML (h = 0..3), mesmo que antigo
    ciclo: list[Previsao]
    # o servico de ML so roda para tanque ativo e com especie
    elegivel: bool
    previsao_valida: bool
    nivel_risco: str | None

    @property
    def od(self) -> Previsao | None:
        return next((p for p in self.ciclo if p.horizonte_h == 0), None)

    @property
    def gerada_em(self) -> datetime | None:
        return self.ciclo[0].ts_previsao if self.ciclo else None

    @property
    def ultima_leitura_em(self) -> datetime | None:
        return max(self.ultima_por_dispositivo.values(), default=None)


def status_conexao(ultima_leitura: datetime | None, agora: datetime) -> str:
    return "online" if ultima_leitura is not None and agora - ultima_leitura <= LIMITE_OFFLINE else "offline"


def ultimas_leituras(sessao: Session, ids_tanques: list[int]) -> list[UltimaLeitura]:
    """Leitura mais recente de cada sensor dos tanques (usa o indice ix_leituras_sensor_ts)."""
    ultima = (
        select(Leitura.valor, Leitura.unidade, Leitura.ts)
        .where(Leitura.id_sensor == Sensor.id)
        .order_by(Leitura.ts.desc())
        .limit(1)
        .lateral()
    )
    linhas = sessao.execute(
        select(
            Sensor.id_tanque, Sensor.id_dispositivo, TipoSensor.grandeza, ultima.c.valor, ultima.c.unidade, ultima.c.ts
        )
        .join(TipoSensor, TipoSensor.id == Sensor.id_tipo)
        .join(ultima, true())
        .where(Sensor.id_tanque.in_(ids_tanques))
    ).all()
    return [UltimaLeitura(*linha) for linha in linhas]


def ultimos_ciclos(sessao: Session, ids_tanques: list[int]) -> dict[int, list[Previsao]]:
    """As 4 linhas que o servico de ML grava por ciclo compartilham o mesmo ts_previsao."""
    ultimo = (
        select(Previsao.id_tanque, func.max(Previsao.ts_previsao).label("ts"))
        .where(Previsao.id_tanque.in_(ids_tanques))
        .group_by(Previsao.id_tanque)
        .subquery()
    )
    previsoes = sessao.scalars(
        select(Previsao)
        .join(ultimo, (ultimo.c.id_tanque == Previsao.id_tanque) & (ultimo.c.ts == Previsao.ts_previsao))
        .order_by(Previsao.horizonte_h)
    ).all()
    ciclos: dict[int, list[Previsao]] = {}
    for previsao in previsoes:
        ciclos.setdefault(previsao.id_tanque, []).append(previsao)
    return ciclos


def _nivel_atual(leituras: dict[str, UltimaLeitura], od: Previsao, especie: Especie) -> str:
    # pior entre pH e temperatura da ultima leitura e o OD estimado (nivel_geral do ML);
    # o nivel do OD e o que o ML gravou, a API nao reclassifica
    niveis = [od.nivel_risco] + [
        faixas.nivel(float(leituras[g].valor), g, especie) for g in ("ph", "temperatura") if g in leituras
    ]
    return faixas.pior(*niveis)


def carregar_situacoes(
    sessao: Session, tanques: list[Tanque], especies: dict[int, Especie], agora: datetime
) -> dict[int, SituacaoTanque]:
    ids = [t.id for t in tanques]
    leituras_por_tanque: dict[int, list[UltimaLeitura]] = {}
    for leitura in ultimas_leituras(sessao, ids):
        leituras_por_tanque.setdefault(leitura.id_tanque, []).append(leitura)
    ciclos = ultimos_ciclos(sessao, ids)

    situacoes = {}
    for tanque in tanques:
        mais_recentes: dict[str, UltimaLeitura] = {}
        por_dispositivo: dict[int, datetime] = {}
        for leitura in leituras_por_tanque.get(tanque.id, []):
            atual = mais_recentes.get(leitura.grandeza)
            if atual is None or leitura.ts > atual.ts:
                mais_recentes[leitura.grandeza] = leitura
            anterior = por_dispositivo.get(leitura.id_dispositivo, leitura.ts)
            por_dispositivo[leitura.id_dispositivo] = max(leitura.ts, anterior)

        especie = especies.get(tanque.id_especie) if tanque.id_especie is not None else None
        ciclo = ciclos.get(tanque.id, [])
        elegivel = tanque.status == "ativo" and especie is not None
        od = next((p for p in ciclo if p.horizonte_h == 0), None)
        valida = elegivel and od is not None and agora - od.ts_previsao <= LIMITE_PREVISAO
        situacoes[tanque.id] = SituacaoTanque(
            leituras=mais_recentes,
            ultima_por_dispositivo=por_dispositivo,
            ciclo=ciclo,
            elegivel=elegivel,
            previsao_valida=valida,
            nivel_risco=_nivel_atual(mais_recentes, od, especie) if valida else None,
        )
    return situacoes
