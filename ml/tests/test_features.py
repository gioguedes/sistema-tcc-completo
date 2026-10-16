import numpy as np
import pandas as pd
import pytest

from src.faixas import FaixaEspecie
from src.features import calcular_features, cobertura, nomes_features, para_grade_15min

FAIXA_REDONDA = FaixaEspecie(ph_min=0, ph_max=10, temp_min=0, temp_max=10, od_min=0, od_max=10)


def _serie(ph, temperatura=None, od=None, inicio="2026-01-01 00:00") -> pd.DataFrame:
    n = len(ph)
    indice = pd.date_range(inicio, periods=n, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "ph": ph,
            "temperatura": temperatura if temperatura is not None else [5.0] * n,
            "od": od if od is not None else [5.0] * n,
        },
        index=indice,
    )


def test_grade_alinha_blocos_em_00_15_30_45_e_nao_interpola():
    df = pd.DataFrame(
        {
            "ts": pd.to_datetime(
                ["2023-01-01 00:07", "2023-01-01 00:14", "2023-01-01 00:15", "2023-01-01 01:01"], utc=True
            ),
            "ph": [7.0, 7.4, 8.0, 6.0],
        }
    )
    grade = para_grade_15min(df, ["ph"])
    assert list(grade.index.strftime("%H:%M")) == ["00:00", "00:15", "00:30", "00:45", "01:00"]
    assert grade["ph"].iloc[0] == pytest.approx(7.2)
    assert grade["ph"].iloc[1] == pytest.approx(8.0)
    assert grade["ph"].iloc[2:4].isna().all()
    assert grade["ph"].iloc[4] == pytest.approx(6.0)


def test_serie_de_5_minutos_vira_mediana_de_3_leituras_por_bloco():
    ts = pd.date_range("2023-07-01 00:00", periods=6, freq="5min", tz="UTC")
    df = pd.DataFrame({"ts": ts, "od": [5.0, 9.0, 6.0, 7.0, 7.0, 1.0]})
    grade = para_grade_15min(df, ["od"])
    assert list(grade["od"]) == [6.0, 7.0]


def test_nomes_features_tem_15_variaveis_na_ordem_fixa():
    nomes = nomes_features()
    assert len(nomes) == 15
    assert nomes[:5] == ["ph_ultimo", "ph_media_30", "ph_media_60", "ph_incl_30", "ph_incl_60"]


def test_rampa_da_inclinacao_exata():
    # pH sobe 0,25 por bloco = 1,0 por hora = 0,1 da faixa por hora
    ultima = calcular_features(_serie(ph=[0.25 * i for i in range(9)]), FAIXA_REDONDA).iloc[-1]
    assert ultima["ph_incl_30"] == pytest.approx(0.1)
    assert ultima["ph_incl_60"] == pytest.approx(0.1)
    assert ultima["ph_ultimo"] == pytest.approx(0.2)
    # média dos 2 últimos blocos (1,75 e 2,0) e dos 4 últimos (1,25 a 2,0)
    assert ultima["ph_media_30"] == pytest.approx(0.1875)
    assert ultima["ph_media_60"] == pytest.approx(0.1625)


def test_serie_constante_tem_inclinacao_zero_e_media_igual_ao_valor():
    ultima = calcular_features(_serie(ph=[7.0] * 6), FAIXA_REDONDA).iloc[-1]
    assert ultima["ph_incl_60"] == pytest.approx(0.0)
    assert ultima["ph_media_60"] == pytest.approx(0.7)


def test_sem_4_blocos_de_historico_a_inclinacao_de_60_e_nan():
    ultima = calcular_features(_serie(ph=[7.0] * 4), FAIXA_REDONDA).iloc[-1]
    assert np.isnan(ultima["ph_incl_60"])
    assert not np.isnan(ultima["ph_incl_30"])


def test_media_exige_2_3_dos_blocos_arredondando_para_baixo():
    # 60 min = 4 blocos: precisa de 2 preenchidos; 30 min = 2 blocos: precisa de 1
    com_dois = calcular_features(_serie(ph=[7.0, np.nan, np.nan, 7.0]), FAIXA_REDONDA).iloc[-1]
    com_um = calcular_features(_serie(ph=[np.nan, np.nan, np.nan, 7.0]), FAIXA_REDONDA).iloc[-1]
    assert com_dois["ph_media_60"] == pytest.approx(0.7)
    assert np.isnan(com_um["ph_media_60"])
    assert com_um["ph_media_30"] == pytest.approx(0.7)


def test_variaveis_em_t_nao_dependem_do_futuro():
    base = [7.0] * 40
    com_pico = base.copy()
    com_pico[30] = 9.9
    t = 20
    antes = calcular_features(_serie(ph=base), FAIXA_REDONDA).iloc[t]
    depois = calcular_features(_serie(ph=com_pico), FAIXA_REDONDA).iloc[t]
    pd.testing.assert_series_equal(antes, depois)


def test_cobertura_conta_blocos_com_ph_e_temperatura():
    ph = [7.0, np.nan, 7.0, 7.0, 7.0]
    temperatura = [5.0, 5.0, 5.0, np.nan, 5.0]
    # últimos 4 blocos: sem pH, ok, sem temperatura, ok
    assert cobertura(_serie(ph=ph, temperatura=temperatura)).iloc[-1] == 2
