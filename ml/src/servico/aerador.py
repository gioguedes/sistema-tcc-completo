"""Aerador automático: liga/desliga com histerese pelo OD estimado e pelo OD projetado para 1 h.

Controle liga/desliga clássico, o mais usado na prática (Li, Zou e Jiang, 2022). A histerese
(liga abaixo de `liga_od`, desliga só acima de `desliga_od`) evita que o relé fique batendo
quando o OD oscila perto do limite. O registro em `acionamentos_atuador` e o comando MQTT seguem
o mesmo protocolo do comando manual da API (backend/src/api/comando_aerador.py).
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

import paho.mqtt.client as mqtt
from sqlalchemy import Engine, text

from src.servico.inferencia import Previsao

logger = logging.getLogger(__name__)

TEMPO_LIMITE_S = 5.0
TAMANHO_MOTIVO = 160  # VARCHAR(160) em acionamentos_atuador


@dataclass(frozen=True)
class LimitesAerador:
    liga_od: float
    desliga_od: float
    pausa_manual: timedelta
    confianca_min: float


@dataclass(frozen=True)
class UltimoComando:
    acao: str
    automatico: bool
    ts: datetime


def _mg(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def decidir(
    previsoes: list[Previsao], ultimo: UltimoComando | None, limites: LimitesAerador, agora: datetime
) -> tuple[str, str] | None:
    """(acao, motivo) quando o estado do aerador deve mudar; None para deixar como está."""
    od = previsoes[0]
    if od.confianca < limites.confianca_min:
        return None
    # quem cuida do tanque manda: o automático espera a pausa depois de um comando manual
    if ultimo is not None and not ultimo.automatico and agora - ultimo.ts < limites.pausa_manual:
        return None

    od_1h = next((p.valor_previsto for p in previsoes if p.horizonte_h == 1 and p.parametro_critico == "od"), None)
    ligado = ultimo is not None and ultimo.acao == "ligar"
    projecao = f" (previsto em 1 h: {_mg(od_1h)})" if od_1h is not None else ""

    if not ligado and min(od.valor_previsto, od_1h if od_1h is not None else od.valor_previsto) < limites.liga_od:
        motivo = f"Automático: OD estimado {_mg(od.valor_previsto)} mg/L{projecao}, abaixo de {_mg(limites.liga_od)}."
        return "ligar", motivo[:TAMANHO_MOTIVO]
    # só desliga o que ele mesmo ligou: um aerador ligado à mão continua ligado
    if (
        ligado
        and ultimo.automatico
        and od.valor_previsto >= limites.desliga_od
        and (od_1h is None or od_1h >= limites.desliga_od)
    ):
        motivo = f"Automático: OD estimado {_mg(od.valor_previsto)} mg/L{projecao}, acima de {_mg(limites.desliga_od)}."
        return "desligar", motivo[:TAMANHO_MOTIVO]
    return None


class Publicador(Protocol):
    def publicar_aerador(self, mac: str, acao: str, id_acionamento: int, ts: int) -> bool: ...


def topico_aerador(prefixo: str, mac: str) -> str:
    return f"{prefixo}/{mac.replace(':', '').lower()}/aerador"


class PublicadorMqtt:
    def __init__(self, broker_host: str, broker_port: int, topico_prefixo: str) -> None:
        self._prefixo = topico_prefixo
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ml-aerador-{uuid.uuid4().hex[:8]}")
        self._client.connect_async(broker_host, broker_port)
        self._client.loop_start()

    def publicar_aerador(self, mac: str, acao: str, id_acionamento: int, ts: int) -> bool:
        if not self._client.is_connected():
            logger.warning("comando automatico do aerador nao enviado: sem conexao com o broker")
            return False
        topico = topico_aerador(self._prefixo, mac)
        mensagem = self._client.publish(
            topico, json.dumps({"acao": acao, "id": id_acionamento, "ts": ts}), qos=1, retain=True
        )
        try:
            mensagem.wait_for_publish(TEMPO_LIMITE_S)
        except (RuntimeError, ValueError):
            logger.exception("falha ao publicar em %s", topico)
            return False
        return mensagem.is_published()


SQL_ID_PREVISAO_OD = text(
    "SELECT id FROM previsoes WHERE id_tanque = :t AND ts_previsao = :ts AND horizonte_h = 0 ORDER BY id DESC LIMIT 1"
)
SQL_DISPOSITIVOS = text("SELECT id, mac_address FROM dispositivos WHERE id_tanque = :t ORDER BY id")
SQL_ULTIMO = text(
    "SELECT acao, id_previsao IS NOT NULL AS automatico, ts_acionamento FROM acionamentos_atuador "
    "WHERE id_dispositivo = :d ORDER BY ts_acionamento DESC, id DESC LIMIT 1"
)
SQL_INSERIR = text(
    "INSERT INTO acionamentos_atuador (id_dispositivo, id_tanque, id_previsao, acao, motivo, ts_acionamento) "
    "VALUES (:d, :t, :p, :acao, :motivo, :ts) RETURNING id"
)


class ControleAerador:
    def __init__(self, limites: LimitesAerador, publicador: Publicador) -> None:
        self._limites = limites
        self._publicador = publicador

    def aplicar(self, engine: Engine, id_tanque: int, previsoes: list[Previsao], agora: datetime) -> int:
        """Comanda o aerador de cada dispositivo do tanque; devolve quantos comandos saíram."""
        enviados = 0
        with engine.connect() as conn:
            id_previsao = conn.execute(SQL_ID_PREVISAO_OD, {"t": id_tanque, "ts": agora}).scalar_one()
            dispositivos = conn.execute(SQL_DISPOSITIVOS, {"t": id_tanque}).all()

        for id_dispositivo, mac in dispositivos:
            with engine.connect() as conn:
                transacao = conn.begin()
                linha = conn.execute(SQL_ULTIMO, {"d": id_dispositivo}).first()
                ultimo = UltimoComando(*linha) if linha else None
                decisao = decidir(previsoes, ultimo, self._limites, agora)
                if decisao is None:
                    transacao.rollback()
                    continue
                acao, motivo = decisao
                id_acionamento = conn.execute(
                    SQL_INSERIR,
                    {"d": id_dispositivo, "t": id_tanque, "p": id_previsao, "acao": acao, "motivo": motivo, "ts": agora},
                ).scalar_one()
                if not self._publicador.publicar_aerador(mac, acao, id_acionamento, int(agora.timestamp())):
                    # sem confirmação do broker o comando não saiu: não fica registro de um acionamento que não houve
                    transacao.rollback()
                    logger.warning("tanque %d: aerador automatico (%s) nao enviado; tenta no proximo ciclo", id_tanque, acao)
                    continue
                transacao.commit()
            logger.info("tanque %d: aerador %s (%s)", id_tanque, acao, motivo)
            enviados += 1
        return enviados
