import logging

from sqlalchemy import func, select

from src.db.models import Leitura
from src.db.seed import MAC_DISPOSITIVO_PADRAO, semear
from src.mqtt.processor import LeituraProcessor
from src.mqtt.schemas import LeituraMqttPayload

MAC_SEM_SEPARADOR = MAC_DISPOSITIVO_PADRAO.replace(":", "")


def _payload(ts: int, **sobrescritas: float | None) -> LeituraMqttPayload:
    valores = {"ph": 6.8, "temperatura": 27.9, "turbidez": 11.7}
    valores.update(sobrescritas)
    return LeituraMqttPayload(mac=MAC_SEM_SEPARADOR, ts=ts, **valores)


def _total_leituras(session) -> int:
    return session.scalar(select(func.count()).select_from(Leitura))


def test_payload_novo_insere_uma_linha_por_grandeza(db_session):
    semear(db_session)
    db_session.commit()

    processor = LeituraProcessor()
    inseridas = processor.processar_payload(db_session, _payload(ts=1758499200))

    assert inseridas == 3
    assert _total_leituras(db_session) == 3


def test_payload_republicado_nao_duplica(db_session):
    semear(db_session)
    db_session.commit()

    processor = LeituraProcessor()
    processor.processar_payload(db_session, _payload(ts=1758499200))
    segunda_tentativa = processor.processar_payload(db_session, _payload(ts=1758499200))

    assert segunda_tentativa == 0
    assert _total_leituras(db_session) == 3


def test_grandeza_nula_nao_gera_linha(db_session):
    semear(db_session)
    db_session.commit()

    processor = LeituraProcessor()
    inseridas = processor.processar_payload(db_session, _payload(ts=1758499200, ph=None))

    assert inseridas == 2
    assert _total_leituras(db_session) == 2


def test_mac_desconhecido_descarta_e_loga(db_session, caplog):
    processor = LeituraProcessor()
    payload = LeituraMqttPayload(mac="ffffffffffff", ts=1758499200, ph=6.8, temperatura=27.9, turbidez=11.7)

    with caplog.at_level(logging.WARNING):
        inseridas = processor.processar_payload(db_session, payload)

    assert inseridas == 0
    assert _total_leituras(db_session) == 0
    assert "nao cadastrado" in caplog.text