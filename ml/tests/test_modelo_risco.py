import numpy as np
import pandas as pd
import pytest

from src.faixas import CRITICO, OTIMO, TILAPIA, nivel_geral
from src.features import nomes_features
from src.treino.modelo_od import treinar_od_central
from src.treino.modelo_risco import (
    avaliar_risco, montar_dataset_risco, prever_risco, treinar_classificador, treinar_risco,
)
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


def _od_sintetico():
    bruto = leituras_sinteticas(dias=4)
    return treinar_od_central(bruto[bruto["grupo"] != "lago_d"], 20)


def test_avaliar_risco_mede_os_tres_modelos_por_horizonte():
    dataset = _dataset_sintetico()
    treino, teste = dataset[dataset["grupo"] != "lago_d"], dataset[dataset["grupo"] == "lago_d"]
    resultado = avaliar_risco(treino, teste, _od_sintetico(), TILAPIA, 20)
    assert set(resultado) == {1, 2, 3}
    assert set(resultado[1]) == {"xgboost", "classificador", "persistencia", "distribuicao_teste"}
    assert set(resultado[1]["xgboost"]) == {"acuracia", "f1_macro", "recall_critico", "matriz_confusao"}
    assert sum(resultado[1]["distribuicao_teste"]) == sum(map(sum, resultado[1]["persistencia"]["matriz_confusao"]))


def test_treino_sem_uma_das_classes_da_erro_claro():
    serie = _serie_constante(60, ph=7.5)
    dataset = montar_dataset_risco({"p": serie}, {"p": "lago"}, TILAPIA, cobertura_min_blocos=3)
    with pytest.raises(ValueError, match="sem exemplos das classes"):
        treinar_classificador(dataset, n_estimadores=5)


def test_pacote_sintetico_tem_modelos_e_metadados():
    pacote = pacote_sintetico()
    assert pacote["versao"] == 3
    assert pacote["features"] == nomes_features()
    assert set(pacote["od"]) == {"od", "od_q10", "od_q90"}
    assert set(pacote["risco"]) == {1, 2, 3}
    assert set(pacote["risco"][1]) == {"ph", "temperatura"}
    assert set(pacote["risco"][1]["ph"]) == {"centro", "q10", "q90"}
    assert set(pacote["dominio_od"]) == {"temperatura", "ph"}
    assert pacote["faixa_treino"]["ph_min"] == 6.5


def test_alvo_da_dinamica_e_a_variacao_ate_t_mais_h():
    serie = _serie_constante(40, ph=7.0)
    serie["ph"] = 7.0 + 0.01 * np.arange(40)
    dataset = montar_dataset_risco({"p": serie}, {"p": "lago"}, TILAPIA, cobertura_min_blocos=3)
    linha = dataset.loc[serie.index[10]]
    # 1 h = 4 blocos de 15 min
    assert linha["var_ph_h1"] == pytest.approx(0.04)
    assert linha["var_ph_h3"] == pytest.approx(0.12)
    assert linha["ph_agora"] == pytest.approx(7.10)


class _Constante:
    def __init__(self, valor):
        self.valor = valor

    def predict(self, X):
        return np.full(len(X), self.valor)


def test_variacao_zero_e_a_persistencia_e_a_regra_e_a_do_rotulo():
    dataset = _dataset_sintetico().iloc[:200]
    zero = {g: {n: _Constante(0.0) for n in ("centro", "q10", "q90")} for g in ("ph", "temperatura")}
    od_fixo = _Constante(6.0)
    nivel, confianca, valores = prever_risco(zero, od_fixo, dataset, TILAPIA)
    esperado = nivel_geral(dataset["ph_agora"], dataset["temperatura_agora"], np.full(len(dataset), 6.0), TILAPIA)
    assert (nivel == esperado).all()
    # todos os cenários iguais: confiança máxima
    assert (confianca == 1.0).all()
    assert np.allclose(valores["ph"], dataset["ph_agora"])


def test_confianca_cai_quando_os_cenarios_cruzam_a_borda():
    linhas = _dataset_sintetico().iloc[:1].copy()
    linhas["ph_agora"], linhas["temperatura_agora"] = 7.0, 25.0
    modelos = {
        "ph": {"centro": _Constante(0.0), "q10": _Constante(-3.0), "q90": _Constante(0.0)},
        "temperatura": {n: _Constante(0.0) for n in ("centro", "q10", "q90")},
    }
    nivel, confianca, _ = prever_risco(modelos, _Constante(6.0), linhas, TILAPIA)
    # pH 4,0 nos 2 cenários com q10: 3 de 5 concordam com o centro (ótimo)
    assert nivel[0] == OTIMO
    assert confianca[0] == pytest.approx(0.6)


def test_dinamica_treinada_preve_a_tendencia_melhor_que_zero():
    dataset = _dataset_sintetico()
    treino, teste = dataset[dataset["grupo"] != "lago_d"], dataset[dataset["grupo"] == "lago_d"].dropna(subset=["var_temperatura_h1"])
    modelos = treinar_risco(treino, 30)
    previsto = modelos[1]["temperatura"]["centro"].predict(teste[nomes_features()])
    real = teste["var_temperatura_h1"].to_numpy()
    assert np.mean(np.abs(previsto - real)) < np.mean(np.abs(real))
