import numpy as np
import pandas as pd
import pytest

from src.faixas import CRITICO, OTIMO, TILAPIA
from src.treino.preparar import grupos_dos_pontos, series_por_ponto
from src.treino.rotulos import rotular
from src.treino.split import (
    escolher_grupos_teste,
    linhas_por_grupo,
    split_temporal,
    validacao_cruzada,
)


def test_split_escolhe_corpos_que_somam_perto_de_15_por_cento():
    linhas = {"a": 500, "b": 150, "c": 200, "d": 100, "e": 50}
    assert escolher_grupos_teste(linhas) == ["b"]


def test_split_empate_prefere_menos_corpos():
    linhas = {"a": 850, "b": 150, "c": 100, "d": 50}
    assert escolher_grupos_teste(linhas) == ["b"]


def test_split_com_um_corpo_so_da_erro():
    with pytest.raises(ValueError):
        escolher_grupos_teste({"a": 100})


def test_pontos_do_mesmo_lago_ficam_do_mesmo_lado():
    linhas_por_ponto = {"lh1": 50, "lh2": 50, "lh3": 50, "ly": 60, "lu": 40, "sl": 70, "wi": 40}
    grupo_de = {"lh1": "lh", "lh2": "lh", "lh3": "lh", "ly": "ly", "lu": "lu", "sl": "sl", "wi": "wi"}
    por_grupo = linhas_por_grupo(linhas_por_ponto, grupo_de)
    assert por_grupo["lh"] == 150
    teste = escolher_grupos_teste(por_grupo)
    lados = {ponto in [p for p, g in grupo_de.items() if g in teste] for ponto in ("lh1", "lh2", "lh3")}
    assert len(lados) == 1


def test_series_por_ponto_na_grade_de_15_min():
    limpo = pd.DataFrame(
        {
            "ponto": ["p1", "p1", "p1", "p2"],
            "grupo": ["lago_a", "lago_a", "lago_a", "lago_a"],
            "ts": pd.to_datetime(["2023-01-01 00:00", "2023-01-01 00:05", "2023-01-01 00:45", "2023-01-01 00:00"], utc=True),
            "temperatura": [20.0, 22.0, 21.0, 25.0],
            "od": [6.0, 8.0, 7.0, 5.0],
            "ph": [7.0, 7.2, 7.1, 8.0],
        }
    )
    series = series_por_ponto(limpo)
    assert set(series) == {"p1", "p2"}
    assert list(series["p1"].columns) == ["temperatura", "ph", "od"]
    assert len(series["p1"]) == 4
    assert series["p1"]["od"].iloc[0] == pytest.approx(7.0)
    assert series["p1"].iloc[1:3].isna().all(axis=None)
    assert grupos_dos_pontos(limpo) == {"p1": "lago_a", "p2": "lago_a"}


def _serie_constante(blocos: int, ph: float) -> pd.DataFrame:
    indice = pd.date_range("2023-01-01", periods=blocos, freq="15min", tz="UTC")
    return pd.DataFrame({"ph": ph, "temperatura": 25.0, "od": 6.0}, index=indice)


def test_rotulo_olha_4h_blocos_a_frente():
    serie = _serie_constante(100, ph=7.5)
    serie.iloc[50:, serie.columns.get_loc("ph")] = 4.5
    rotulo = rotular(serie, TILAPIA, horizonte_h=2)
    # h = 2 são 8 blocos: a linha 41 olha o bloco 49 (ainda ótimo), a 42 olha o 50
    assert rotulo.iloc[41] == OTIMO
    assert rotulo.iloc[42] == CRITICO
    assert np.isnan(rotulo.iloc[-1])


def test_rotulo_usa_o_od_medido():
    serie = _serie_constante(20, ph=7.5)
    serie["od"] = 2.0
    assert rotular(serie, TILAPIA, horizonte_h=1).iloc[0] == CRITICO


def test_split_temporal_separa_2023_de_2024_em_utc():
    indice = pd.to_datetime(["2023-12-31 23:45", "2024-01-01 00:00", "2024-06-01 00:00"], utc=True)
    df = pd.DataFrame({"x": [1, 2, 3]}, index=indice)
    treino, teste = split_temporal(df)
    assert list(treino["x"]) == [1]
    assert list(teste["x"]) == [2, 3]


def test_validacao_cruzada_deixa_cada_corpo_de_fora_e_tira_a_media():
    df = pd.DataFrame({"grupo": ["a", "a", "b", "c"], "v": [1.0, 3.0, 5.0, 7.0]})

    def avaliar(treino, teste):
        assert set(treino["grupo"]).isdisjoint(set(teste["grupo"]))
        return {"modelo": {"mae": float(teste["v"].mean()), "matriz": [len(teste), 1]}}

    resultado = validacao_cruzada(df, avaliar)
    assert list(resultado["por_grupo"]) == ["a", "b", "c"]
    assert resultado["por_grupo"]["a"]["modelo"]["mae"] == 2.0
    # números: média entre corpos; listas: somadas
    assert resultado["media"]["modelo"]["mae"] == pytest.approx((2.0 + 5.0 + 7.0) / 3)
    assert resultado["media"]["modelo"]["matriz"] == [4, 3]
