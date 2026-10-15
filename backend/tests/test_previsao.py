import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.db.models import Previsao, Tanque
from src.db.seed import semear


def _previsao(id_tanque: int, **sobrescritas) -> Previsao:
    valores = {
        "id_tanque": id_tanque,
        "parametro_critico": "od",
        "valor_previsto": 5.2,
        "nivel_risco": "otimo",
        "horizonte_h": 0,
        "confianca": 0.8,
    }
    valores.update(sobrescritas)
    return Previsao(**valores)


def _id_tanque(db_session) -> int:
    semear(db_session)
    db_session.commit()
    return db_session.scalar(select(Tanque.id))


def test_horizonte_zero_e_aceito_e_ts_previsao_tem_default(db_session):
    previsao = _previsao(_id_tanque(db_session))
    db_session.add(previsao)
    db_session.flush()
    db_session.refresh(previsao)
    assert previsao.ts_previsao is not None


@pytest.mark.parametrize(
    "sobrescrita",
    [{"horizonte_h": 4}, {"nivel_risco": "indeterminado"}, {"confianca": 1.5}, {"parametro_critico": "amonia"}],
)
def test_checks_do_ddl_continuam_valendo(db_session, sobrescrita):
    db_session.add(_previsao(_id_tanque(db_session), **sobrescrita))
    with pytest.raises(IntegrityError):
        db_session.flush()
