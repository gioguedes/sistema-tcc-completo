from sqlalchemy import select

from src.db.models import Dispositivo, Sensor
from src.db.seed import MAC_DISPOSITIVO_PADRAO, semear


def test_semear_cria_dispositivo_e_tres_sensores(db_session):
    dispositivo = semear(db_session)
    db_session.commit()

    assert dispositivo.mac_address == MAC_DISPOSITIVO_PADRAO
    sensores = db_session.scalars(
        select(Sensor).where(Sensor.id_dispositivo == dispositivo.id)
    ).all()
    assert len(sensores) == 3


def test_semear_e_idempotente(db_session):
    semear(db_session)
    db_session.commit()
    semear(db_session)
    db_session.commit()

    dispositivos = db_session.scalars(
        select(Dispositivo).where(Dispositivo.mac_address == MAC_DISPOSITIVO_PADRAO)
    ).all()
    assert len(dispositivos) == 1

    sensores = db_session.scalars(
        select(Sensor).where(Sensor.id_dispositivo == dispositivos[0].id)
    ).all()
    assert len(sensores) == 3