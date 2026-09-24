import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.db.models import Dispositivo, Leitura, Sensor, TipoSensor
from src.mqtt.schemas import LeituraMqttPayload

logger = logging.getLogger(__name__)


def _carregar_cache_sensores(session: Session) -> dict[str, dict[str, tuple[int, str]]]:
    linhas = session.execute(
        select(Dispositivo.mac_address, TipoSensor.grandeza, Sensor.id, TipoSensor.unidade)
        .join(Sensor, Sensor.id_dispositivo == Dispositivo.id)
        .join(TipoSensor, TipoSensor.id == Sensor.id_tipo)
    ).all()

    cache: dict[str, dict[str, tuple[int, str]]] = {}
    for mac_address, grandeza, id_sensor, unidade in linhas:
        cache.setdefault(mac_address, {})[grandeza] = (id_sensor, unidade)
    return cache


class LeituraProcessor:
    def __init__(self) -> None:
        self._cache: dict[str, dict[str, tuple[int, str]]] = {}

    def processar_payload(self, session: Session, payload: LeituraMqttPayload) -> int:
        mac = payload.mac_com_separador
        sensores = self._resolver_sensores(session, mac)
        if sensores is None:
            logger.warning("dispositivo %s nao cadastrado, leitura descartada", mac)
            return 0

        linhas_inseridas = 0
        for grandeza, valor in payload.valores_por_grandeza().items():
            dados_sensor = sensores.get(grandeza)
            if dados_sensor is None:
                logger.warning("dispositivo %s sem sensor de %s cadastrado, leitura descartada", mac, grandeza)
                continue

            id_sensor, unidade = dados_sensor
            resultado = session.execute(
                pg_insert(Leitura)
                .values(id_sensor=id_sensor, valor=valor, unidade=unidade, ts=payload.ts_utc)
                .on_conflict_do_nothing(index_elements=["id_sensor", "ts"])
                .returning(Leitura.id)
            )
            # rowcount do driver nao e confiavel aqui (retorna -1 com
            # ON CONFLICT DO NOTHING); RETURNING so traz linha quando o
            # insert realmente aconteceu.
            if resultado.first() is not None:
                linhas_inseridas += 1

        session.commit()
        return linhas_inseridas

    def _resolver_sensores(self, session: Session, mac: str) -> dict[str, tuple[int, str]] | None:
        if mac not in self._cache:
            # recarrega tudo, nao so o mac que faltou: cobre o dispositivo
            # cadastrado depois do processo ja estar de pe (Tarefa 5 pode
            # rodar a qualquer momento, sem reiniciar a ingestao).
            self._cache = _carregar_cache_sensores(session)
        return self._cache.get(mac)