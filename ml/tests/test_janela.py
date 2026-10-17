from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src.faixas import TILAPIA
from src.servico.janela import BLOCOS_JANELA, ler_janela, tanques_ativos
from tests.banco import inserir_leituras, semear_tanque

AGORA = datetime(2026, 9, 24, 12, 0, 30, tzinfo=timezone.utc)


def _com_leituras(conn, minutos: int, ph: float = 7.5, **kwargs) -> dict:
    ids = semear_tanque(conn, **kwargs)
    inicio = AGORA - timedelta(minutes=minutos - 1)
    inserir_leituras(conn, ids["sensores"]["ph"], inicio, [ph] * minutos)
    inserir_leituras(conn, ids["sensores"]["temperatura"], inicio, [26.0] * minutos)
    return ids


def test_janela_tem_6_blocos_terminando_no_bloco_de_agora(db):
    with db.begin() as conn:
        ids = _com_leituras(conn, minutos=60)
        janela = ler_janela(conn, ids["id_tanque"], AGORA)
    assert len(janela) == BLOCOS_JANELA == 6
    assert list(janela.columns) == ["ph", "temperatura"]
    assert janela.index[0] == pd.Timestamp("2026-09-24 10:45", tz="UTC")
    assert janela.index[-1] == pd.Timestamp("2026-09-24 12:00", tz="UTC")
    # 60 leituras de 11:01:30 a 12:00:30: o bloco 10:45 fica vazio, os outros 5 têm dado
    assert janela["ph"].notna().sum() == 5


def test_janela_ignora_outros_tanques(db):
    with db.begin() as conn:
        ids = _com_leituras(conn, minutos=90)
        _com_leituras(conn, minutos=90, ph=4.0, mac="00:00:00:00:00:01")
        janela = ler_janela(conn, ids["id_tanque"], AGORA)
    assert (janela["ph"] == 7.5).all()


def test_bloco_e_a_mediana_das_leituras(db):
    with db.begin() as conn:
        ids = semear_tanque(conn)
        inicio = datetime(2026, 9, 24, 11, 30, tzinfo=timezone.utc)
        inserir_leituras(conn, ids["sensores"]["ph"], inicio, [7.0, 7.2, 9.9])
        inserir_leituras(conn, ids["sensores"]["temperatura"], inicio, [26.0, 26.0, 26.0])
        janela = ler_janela(conn, ids["id_tanque"], AGORA)
    assert janela.loc[pd.Timestamp("2026-09-24 11:30", tz="UTC"), "ph"] == pytest.approx(7.2)


def test_leitura_no_inicio_exato_da_janela_entra(db):
    with db.begin() as conn:
        ids = semear_tanque(conn)
        inserir_leituras(conn, ids["sensores"]["ph"], datetime(2026, 9, 24, 10, 45, tzinfo=timezone.utc), [7.0])
        janela = ler_janela(conn, ids["id_tanque"], AGORA)
    assert janela["ph"].iloc[0] == pytest.approx(7.0)
    assert janela["temperatura"].isna().all()


def test_janela_sem_leituras_e_toda_nan(db):
    with db.begin() as conn:
        ids = semear_tanque(conn)
        janela = ler_janela(conn, ids["id_tanque"], AGORA)
    assert len(janela) == BLOCOS_JANELA
    assert janela.isna().all(axis=None)


def test_tanques_ativos_traz_a_faixa_e_pula_inativos(db):
    with db.begin() as conn:
        semear_tanque(conn)
        semear_tanque(conn, mac="00:00:00:00:00:01", status="inativo")
        tanques = tanques_ativos(conn)
    assert len(tanques) == 1
    assert tanques[0][1] == TILAPIA
