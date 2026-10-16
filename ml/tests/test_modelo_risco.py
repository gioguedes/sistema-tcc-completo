import pandas as pd
import pytest

from src.faixas import CRITICO, OTIMO, TILAPIA
from src.features import nomes_features
from src.treino.modelo_risco import avaliar_risco, montar_dataset_risco, treinar_risco
from src.treino.preparar import grupos_dos_pontos, series_por_ponto
from tests.fabricas import leituras_sinteticas, pacote_sintetico


def _serie_constante(blocos: int, ph: float) -> pd.DataFrame:
    indice = pd.date_range("2023-01-01", periods=blocos, freq="15min", tz="UTC")
    return pd.DataFrame({"ph": ph, "temperatura": 25.0, "od": 6.0, "od_estimado": 6.0}, index=indice)


def test_mudar_o_futuro_muda_o_rotulo_mas_nao_as_variaveis():
    t = 40
    serie_a = _serie_constante(100, ph=7.5)
    serie_b = serie_a.copy()
    # joga o pH para fora da faixa só no bloco t + 2h
    serie_b.iloc[t + 8, serie_b.columns.get_loc("ph")] = 4.0

    a = montar_dataset_risco({"p": serie_a}, {"p": "lago"}, TILAPIA, cobertura_min_blocos=3)
    b = montar_dataset_risco({"p": serie_b}, {"p": "lago"}, TILAPIA, cobertura_min_blocos=3)
    instante = serie_a.index[t]
    pd.testing.assert_series_equal(a.loc[instante, nomes_features()], b.loc[instante, nomes_features()])
    assert a.loc[instante, "alvo_h2"] == OTIMO
    assert b.loc[instante, "alvo_h2"] == CRITICO


def test_variaveis_usam_o_od_estimado_e_o_rotulo_o_medido():
    serie = _serie_constante(30, ph=7.5)
    serie["od"] = 2.0
    dataset = montar_dataset_risco({"p": serie}, {"p": "lago"}, TILAPIA, cobertura_min_blocos=3)
    assert (dataset["persistencia"] == OTIMO).all()
    assert (dataset["alvo_h1"].dropna() == CRITICO).all()
    assert (dataset["grupo"] == "lago").all()


def test_cobertura_minima_tira_blocos_do_dataset():
    serie = _serie_constante(30, ph=7.5)
    serie.iloc[[10, 12], serie.columns.get_loc("ph")] = float("nan")
    dataset = montar_dataset_risco({"p": serie}, {"p": "lago"}, TILAPIA, cobertura_min_blocos=3)
    # o bloco 13 tem todas as variáveis, mas só 2 dos últimos 4 blocos (10 e 12
    # vazios), e sai; o 15 tem 3 dos últimos 4 e fica
    assert serie.index[13] not in dataset.index
    assert serie.index[15] in dataset.index


def _dataset_sintetico() -> pd.DataFrame:
    bruto = leituras_sinteticas(dias=4)
    series = series_por_ponto(bruto)
    for serie in series.values():
        serie["od_estimado"] = serie["od"]
    return montar_dataset_risco(series, grupos_dos_pontos(bruto), TILAPIA, cobertura_min_blocos=3)


def test_avaliar_risco_mede_os_tres_modelos_por_horizonte():
    dataset = _dataset_sintetico()
    resultado = avaliar_risco(dataset[dataset["grupo"] != "lago_d"], dataset[dataset["grupo"] == "lago_d"], 20)
    assert set(resultado) == {1, 2, 3}
    assert set(resultado[1]) == {"xgboost", "random_forest", "persistencia", "distribuicao_teste"}
    assert set(resultado[1]["xgboost"]) == {"acuracia", "f1_macro", "recall_critico", "matriz_confusao"}
    assert sum(resultado[1]["distribuicao_teste"]) == sum(map(sum, resultado[1]["persistencia"]["matriz_confusao"]))


def test_treino_sem_uma_das_classes_da_erro_claro():
    serie = _serie_constante(60, ph=7.5)
    dataset = montar_dataset_risco({"p": serie}, {"p": "lago"}, TILAPIA, cobertura_min_blocos=3)
    with pytest.raises(ValueError, match="sem exemplos das classes"):
        treinar_risco(dataset, n_estimadores=5)


def test_pacote_sintetico_tem_modelos_e_metadados():
    pacote = pacote_sintetico()
    assert pacote["versao"] == 2
    assert pacote["features"] == nomes_features()
    assert set(pacote["od"]) == {"od", "od_q10", "od_q90"}
    assert set(pacote["risco"]) == {1, 2, 3}
    assert pacote["faixa_treino"]["ph_min"] == 6.5
