"""Tanques, dispositivos, leituras e previsoes (UC02, UC03, UC06): consultas."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from src.api import series
from src.api.dependencias import Config, Sessao, usuario_atual
from src.api.esquemas import (
    DispositivoSaida,
    EspecieSaida,
    EstimativaOd,
    LeituraAtual,
    Leituras,
    PrevisaoAtual,
    PrevisaoSaida,
    ResumoDispositivo,
    SensorSaida,
    TanqueSaida,
    UltimoAcionamento,
)
from src.api.estado import GRANDEZAS_FISICAS, SituacaoTanque, carregar_situacoes, status_conexao, ultimas_leituras
from src.db.models import AcionamentoAtuador, Dispositivo, Especie, Sensor, Tanque, TipoSensor

# leitura para qualquer usuario autenticado (decisao I-05 da auditoria do front: todos veem todos)
router = APIRouter(tags=["tanques"], dependencies=[Depends(usuario_atual)])

GRANDEZAS = (*GRANDEZAS_FISICAS, "od")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def tanque_ou_404(sessao, id_tanque: int) -> Tanque:
    tanque = sessao.get(Tanque, id_tanque)
    if tanque is None:
        raise HTTPException(404, "Tanque não encontrado.")
    return tanque


def _erro_de_consulta(campo: str, mensagem: str) -> HTTPException:
    return HTTPException(422, [{"loc": ["query", campo], "msg": mensagem, "type": "value_error"}])


def _especies(sessao) -> dict[int, Especie]:
    return {e.id: e for e in sessao.scalars(select(Especie))}


def _baixa_confianca(confianca, config) -> bool:
    return confianca is not None and confianca < config.ml_confianca_min


def _leituras_atuais(situacao: SituacaoTanque, config) -> list[LeituraAtual]:
    # cada grandeza com o seu ts: sensor em falha publica null, a ingestao nao grava,
    # e o painel mostra ha quanto tempo aquele sensor nao le
    atuais = [
        LeituraAtual(grandeza=leitura.grandeza, valor=leitura.valor, unidade=leitura.unidade, ts=leitura.ts)
        for g in GRANDEZAS_FISICAS
        if (leitura := situacao.leituras.get(g))
    ]
    od = situacao.od
    if od is not None:
        atuais.append(
            LeituraAtual(
                grandeza="od",
                valor=od.valor_previsto,
                unidade=series.UNIDADES_PADRAO["od"],
                ts=od.ts_previsao,
                estimado=True,
                baixa_confianca=_baixa_confianca(od.confianca, config),
            )
        )
    return atuais


def montar_tanques(sessao, tanques: list[Tanque], config) -> list[TanqueSaida]:
    agora = _agora()
    especies = _especies(sessao)
    situacoes = carregar_situacoes(sessao, tanques, especies, agora)
    dispositivos: dict[int, list[Dispositivo]] = {}
    for d in sessao.scalars(
        select(Dispositivo).where(Dispositivo.id_tanque.in_([t.id for t in tanques])).order_by(Dispositivo.id)
    ):
        dispositivos.setdefault(d.id_tanque, []).append(d)

    resultado = []
    for t in tanques:
        situacao = situacoes[t.id]
        especie = especies.get(t.id_especie) if t.id_especie is not None else None
        resultado.append(
            TanqueSaida(
                id=t.id,
                nome=t.nome,
                volume_litros=t.volume_litros,
                quantidade_peixes=t.quantidade_peixes,
                data_povoamento=t.data_povoamento,
                status=t.status,
                criado_em=t.criado_em,
                especie=EspecieSaida.model_validate(especie) if especie else None,
                nivel_risco=situacao.nivel_risco,
                ultima_leitura_em=situacao.ultima_leitura_em,
                ultimas_leituras=_leituras_atuais(situacao, config),
                dispositivos=[
                    ResumoDispositivo(
                        id=d.id,
                        nome=d.nome,
                        status_conexao=status_conexao(situacao.ultima_por_dispositivo.get(d.id), agora),
                        ultima_leitura_em=situacao.ultima_por_dispositivo.get(d.id),
                    )
                    for d in dispositivos.get(t.id, [])
                ],
            )
        )
    return resultado


@router.get("/tanques", response_model=list[TanqueSaida])
def listar_tanques(sessao: Sessao, config: Config) -> list[TanqueSaida]:
    tanques = list(sessao.scalars(select(Tanque).order_by(Tanque.id)))
    return montar_tanques(sessao, tanques, config)


@router.get("/tanques/{id_tanque}", response_model=TanqueSaida)
def buscar_tanque(id_tanque: int, sessao: Sessao, config: Config) -> TanqueSaida:
    return montar_tanques(sessao, [tanque_ou_404(sessao, id_tanque)], config)[0]


def sensor_saida(sensor: Sensor, tipo: TipoSensor) -> SensorSaida:
    return SensorSaida(
        id=sensor.id,
        grandeza=tipo.grandeza,
        modelo=tipo.modelo,
        unidade=tipo.unidade,
        status=sensor.status,
        data_instalacao=sensor.data_instalacao,
    )


def ultimo_acionamento(acionamento: AcionamentoAtuador) -> UltimoAcionamento:
    return UltimoAcionamento(
        id=acionamento.id,
        acao=acionamento.acao,
        motivo=acionamento.motivo,
        ts_acionamento=acionamento.ts_acionamento,
        automatico=acionamento.id_previsao is not None,
    )


def montar_dispositivos(sessao, dispositivos: list[Dispositivo]) -> list[DispositivoSaida]:
    agora = _agora()
    sensores: dict[int, list[SensorSaida]] = {}
    for sensor, tipo in sessao.execute(
        select(Sensor, TipoSensor)
        .join(TipoSensor, TipoSensor.id == Sensor.id_tipo)
        .where(Sensor.id_dispositivo.in_([d.id for d in dispositivos]))
        .order_by(Sensor.id)
    ):
        sensores.setdefault(sensor.id_dispositivo, []).append(sensor_saida(sensor, tipo))
    ultima: dict[int, datetime] = {}
    for leitura in ultimas_leituras(sessao, list({d.id_tanque for d in dispositivos})):
        ultima[leitura.id_dispositivo] = max(leitura.ts, ultima.get(leitura.id_dispositivo, leitura.ts))
    acionamentos = {
        a.id_dispositivo: a
        for a in sessao.scalars(
            select(AcionamentoAtuador)
            .where(AcionamentoAtuador.id_dispositivo.in_([d.id for d in dispositivos]))
            .order_by(
                AcionamentoAtuador.id_dispositivo,
                AcionamentoAtuador.ts_acionamento.desc(),
                AcionamentoAtuador.id.desc(),
            )
            .distinct(AcionamentoAtuador.id_dispositivo)
        )
    }

    return [
        DispositivoSaida(
            id=d.id,
            id_tanque=d.id_tanque,
            nome=d.nome,
            modelo_esp32=d.modelo_esp32,
            mac_address=d.mac_address,
            versao_firmware=d.versao_firmware,
            ip_local=str(d.ip_local) if d.ip_local is not None else None,
            status_conexao=status_conexao(ultima.get(d.id), agora),
            ultima_leitura_em=ultima.get(d.id),
            data_cadastro=d.data_cadastro,
            sensores=sensores.get(d.id, []),
            ultimo_acionamento=ultimo_acionamento(acionamentos[d.id]) if d.id in acionamentos else None,
        )
        for d in dispositivos
    ]


@router.get("/tanques/{id_tanque}/dispositivos", response_model=list[DispositivoSaida])
def listar_dispositivos(id_tanque: int, sessao: Sessao) -> list[DispositivoSaida]:
    tanque_ou_404(sessao, id_tanque)
    dispositivos = sessao.scalars(
        select(Dispositivo).where(Dispositivo.id_tanque == id_tanque).order_by(Dispositivo.id)
    ).all()
    return montar_dispositivos(sessao, list(dispositivos))


@router.get("/tanques/{id_tanque}/leituras", response_model=Leituras, response_model_exclude_none=True)
def buscar_leituras(
    id_tanque: int,
    desde: datetime,
    ate: datetime,
    sessao: Sessao,
    bucket: Literal["raw", "5m", "1h"] = "raw",
    grandezas: str | None = None,
) -> Leituras:
    # data sem fuso e lida como UTC
    desde, ate = (d if d.tzinfo else d.replace(tzinfo=timezone.utc) for d in (desde, ate))
    if desde >= ate:
        raise _erro_de_consulta("desde", "O início do período deve ser anterior ao fim.")
    if (ate - desde) / series.PASSOS[bucket] > series.MAX_PONTOS:
        raise _erro_de_consulta("bucket", "Intervalo grande demais para esse agrupamento.")
    pedidas = grandezas.split(",") if grandezas else list(GRANDEZAS)
    if desconhecidas := set(pedidas) - set(GRANDEZAS):
        raise _erro_de_consulta("grandezas", f"Grandeza desconhecida: {', '.join(sorted(desconhecidas))}.")
    tanque_ou_404(sessao, id_tanque)

    unidades = series.unidades_do_tanque(sessao, id_tanque)
    return Leituras(
        id_tanque=id_tanque,
        bucket=bucket,
        desde=desde,
        ate=ate,
        series=[
            {
                "grandeza": g,
                "unidade": unidades[g],
                "estimado": g == "od",
                "pontos": (
                    series.serie_od(sessao, id_tanque, desde, ate, bucket)
                    if g == "od"
                    else series.serie_fisica(sessao, id_tanque, g, desde, ate, bucket)
                ),
            }
            for g in GRANDEZAS
            if g in pedidas
        ],
    )


@router.get("/tanques/{id_tanque}/previsoes/atual", response_model=PrevisaoAtual)
def previsao_atual(id_tanque: int, sessao: Sessao, config: Config) -> PrevisaoAtual:
    tanque = tanque_ou_404(sessao, id_tanque)
    situacao = carregar_situacoes(sessao, [tanque], _especies(sessao), _agora())[tanque.id]
    od = situacao.od
    if not situacao.previsao_valida or od is None:
        # indeterminado (o ML nao gravou) ou desatualizada: sem nivel nem horizontes. O gerada_em
        # do ultimo ciclo fica para o painel dizer "desatualizada desde"; fora do escopo do ML
        # (tanque nao ativo ou sem especie) vai nulo e o painel explica o motivo
        return PrevisaoAtual(
            id_tanque=tanque.id,
            nivel_risco=None,
            gerada_em=situacao.gerada_em if situacao.elegivel else None,
            od_atual=None,
            horizontes=[],
        )
    return PrevisaoAtual(
        id_tanque=tanque.id,
        nivel_risco=situacao.nivel_risco,
        gerada_em=situacao.gerada_em,
        od_atual=EstimativaOd(
            valor=od.valor_previsto,
            nivel_risco=od.nivel_risco,
            confianca=od.confianca,
            baixa_confianca=_baixa_confianca(od.confianca, config),
        ),
        horizontes=[PrevisaoSaida.model_validate(p) for p in situacao.ciclo if p.horizonte_h > 0],
    )
