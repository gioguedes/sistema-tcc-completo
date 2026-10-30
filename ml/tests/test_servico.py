from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from src.faixas import TILAPIA
from src.servico.__main__ import executar_ciclo
from src.servico.inferencia import Inferencia
from tests.banco import inserir_leituras, semear_tanque

AGORA = datetime(2026, 9, 24, 12, 0, 30, tzinfo=timezone.utc)


def _com_leituras(conn, minutos: int, ph=None, termina_em: datetime = AGORA, **kwargs) -> dict:
    ids = semear_tanque(conn, **kwargs)
    inicio = termina_em - timedelta(minutes=minutos - 1)
    inserir_leituras(conn, ids["sensores"]["ph"], inicio, ph or [7.5] * minutos)
    inserir_leituras(conn, ids["sensores"]["temperatura"], inicio, [26.0] * minutos)
    return ids


def _previsoes(conn) -> list:
    return conn.execute(
        text("SELECT horizonte_h, parametro_critico, nivel_risco, confianca FROM previsoes ORDER BY horizonte_h")
    ).all()


def _ciclo(db, pacote) -> dict:
    return executar_ciclo(db, Inferencia(pacote, cobertura_min_blocos=3), confianca_min=0.5, agora=AGORA)


def test_ciclo_grava_4_previsoes_validas(db, pacote):
    with db.begin() as conn:
        _com_leituras(conn, minutos=90)
    assert _ciclo(db, pacote) == {"gravados": 1, "indeterminados": 0, "erros": 0, "aerador": 0}
    with db.connect() as conn:
        linhas = _previsoes(conn)
    assert [l.horizonte_h for l in linhas] == [0, 1, 2, 3]
    assert linhas[0].parametro_critico == "od"
    assert all(l.nivel_risco in ("otimo", "atencao", "critico") for l in linhas)
    assert all(0 <= float(l.confianca) <= 1 for l in linhas)


def test_ct02_ph_caindo_aponta_ph_como_parametro_critico(db, pacote):
    with db.begin() as conn:
        _com_leituras(conn, minutos=90, ph=list(np.linspace(7.0, 4.5, 90)))
    _ciclo(db, pacote)
    with db.connect() as conn:
        linhas = _previsoes(conn)
    assert [l.parametro_critico for l in linhas[1:]] == ["ph", "ph", "ph"]


def test_projecao_nao_sai_da_faixa_fisica(db, pacote):
    with db.begin() as conn:
        # pH despencando ~3 unidades por hora: a projeção linear de 3 h daria negativo
        _com_leituras(conn, minutos=90, ph=list(np.linspace(8.0, 3.4, 90)))
    _ciclo(db, pacote)
    with db.connect() as conn:
        valores = conn.execute(
            text("SELECT valor_previsto FROM previsoes WHERE horizonte_h > 0 ORDER BY horizonte_h")
        ).scalars().all()
    assert [float(v) for v in valores][-1] == 0.0
    assert all(0.0 <= float(v) <= 14.0 for v in valores)


def test_bloco_corrente_ainda_sem_leitura_nao_vira_indeterminado(db, pacote):
    with db.begin() as conn:
        # última leitura às 11:58:30: o bloco das 12:00 está vazio, a janela termina no das 11:45
        _com_leituras(conn, minutos=90, termina_em=AGORA - timedelta(minutes=2))
    assert _ciclo(db, pacote)["gravados"] == 1


def test_no_parado_ha_mais_de_30_min_nao_grava(db, pacote):
    with db.begin() as conn:
        _com_leituras(conn, minutos=90, termina_em=AGORA - timedelta(minutes=40))
    assert _ciclo(db, pacote)["indeterminados"] == 1
    with db.connect() as conn:
        assert _previsoes(conn) == []


def test_cobertura_insuficiente_nao_grava(db, pacote):
    with db.begin() as conn:
        _com_leituras(conn, minutos=90)
        # esvazia os blocos 11:15 e 11:45: sobram 2 dos últimos 4, abaixo do
        # mínimo de 3, mas 11:00 e 11:30 continuam lá e as inclinações existem
        for inicio in ("11:15", "11:45"):
            de = pd.Timestamp(f"2026-09-24 {inicio}", tz="UTC")
            conn.execute(
                text("DELETE FROM leituras WHERE ts >= :de AND ts < :ate"),
                {"de": de, "ate": de + timedelta(minutes=15)},
            )
    assert _ciclo(db, pacote)["indeterminados"] == 1
    with db.connect() as conn:
        assert _previsoes(conn) == []


def test_historico_curto_nao_grava(db, pacote):
    with db.begin() as conn:
        # nó ligado há 45 min: os 4 últimos blocos têm dado, mas o bloco de
        # 60 min atrás (11:00), que a inclinação de 60 min usa, está vazio
        _com_leituras(conn, minutos=45)
    assert _ciclo(db, pacote)["indeterminados"] == 1


def test_erro_em_um_tanque_nao_impede_os_outros(db, pacote, monkeypatch):
    with db.begin() as conn:
        _com_leituras(conn, minutos=90)
        segundo = _com_leituras(conn, minutos=90, mac="00:00:00:00:00:01")

    inferencia = Inferencia(pacote, cobertura_min_blocos=3)
    prever_original = inferencia.prever

    def prever_falha_no_primeiro(janela, faixa, agora):
        if prever_falha_no_primeiro.chamadas == 0:
            prever_falha_no_primeiro.chamadas += 1
            raise RuntimeError("falha simulada")
        return prever_original(janela, faixa, agora)

    prever_falha_no_primeiro.chamadas = 0
    monkeypatch.setattr(inferencia, "prever", prever_falha_no_primeiro)

    contagem = executar_ciclo(db, inferencia, confianca_min=0.5, agora=AGORA)
    assert contagem == {"gravados": 1, "indeterminados": 0, "erros": 1, "aerador": 0}
    with db.connect() as conn:
        tanques = conn.execute(text("SELECT DISTINCT id_tanque FROM previsoes")).scalars().all()
    assert tanques == [segundo["id_tanque"]]


def _janela_completa(fim: str) -> pd.DataFrame:
    indice = pd.date_range(end=pd.Timestamp(fim, tz="UTC"), periods=6, freq="15min")
    return pd.DataFrame({"ph": 7.5, "temperatura": 26.0}, index=indice)


def test_ultimo_bloco_ha_mais_de_30_min_e_indeterminado(pacote):
    # janela montada à mão com as variáveis completas: só a regra de atraso pode recusar
    inferencia = Inferencia(pacote, cobertura_min_blocos=3)
    janela = _janela_completa("2026-09-24 11:45")
    assert inferencia.prever(janela, TILAPIA, datetime(2026, 9, 24, 12, 15, tzinfo=timezone.utc)) is not None
    assert inferencia.prever(janela, TILAPIA, datetime(2026, 9, 24, 12, 16, tzinfo=timezone.utc)) is None


def test_janela_sem_bloco_completo_e_indeterminada(pacote):
    janela = _janela_completa("2026-09-24 12:00").assign(temperatura=np.nan)
    assert Inferencia(pacote, cobertura_min_blocos=3).prever(janela, TILAPIA, AGORA) is None


def test_pacote_com_variaveis_diferentes_nao_inicia(pacote):
    adulterado = {**pacote, "features": pacote["features"][:-1]}
    with pytest.raises(ValueError, match="retreine"):
        Inferencia(adulterado, cobertura_min_blocos=3)


def test_pacote_de_outra_versao_nao_inicia(pacote):
    with pytest.raises(ValueError, match="versão 1"):
        Inferencia({**pacote, "versao": 1}, cobertura_min_blocos=3)
