import numpy as np
import pandas as pd
import pytest

from src.faixas import TILAPIA
from src.treino.modelo_od import comparar_od, metricas_od, od_fora_da_dobra, treinar_od
from src.treino.preparar import grupos_dos_pontos, linhas_validas_od, series_por_ponto
from tests.fabricas import leituras_sinteticas


def _validas() -> pd.DataFrame:
    bruto = leituras_sinteticas(dias=3)
    grupo_de = grupos_dos_pontos(bruto)
    return pd.concat(
        linhas_validas_od(s).assign(ponto=p, grupo=grupo_de[p]) for p, s in series_por_ponto(bruto).items()
    )


def test_treinar_od_gera_o_estimador_e_os_dois_quantis():
    modelos = treinar_od(_validas(), n_estimadores=20)
    assert set(modelos) == {"od", "od_q10", "od_q90"}
    entrada = pd.DataFrame({"temperatura": [25.0], "ph": [7.5]})
    q10, q90 = modelos["od_q10"].predict(entrada)[0], modelos["od_q90"].predict(entrada)[0]
    assert q10 <= q90


def test_od_fora_da_dobra_nao_ve_o_proprio_corpo_dagua():
    # mesmas entradas em todo lugar; só o lago_b tem OD 1,0. Um modelo que
    # tivesse visto o lago_b acertaria perto de 1; fora da dobra ele chuta 9.
    treino = pd.DataFrame(
        {
            "temperatura": [25.0] * 40,
            "ph": [7.5] * 40,
            "od": [9.0] * 30 + [1.0] * 10,
            "grupo": ["lago_a"] * 15 + ["lago_c"] * 15 + ["lago_b"] * 10,
        }
    )
    previsto = od_fora_da_dobra(treino, n_estimadores=20)
    assert previsto[-10:] == pytest.approx([9.0] * 10, abs=0.01)


def test_metricas_e_acuracia_de_faixa():
    m = metricas_od([5.0, 6.0, 2.0], [5.5, 6.0, 3.5], TILAPIA)
    assert m["mae"] == pytest.approx(2.0 / 3)
    # 2,0 é crítico e 3,5 também (OD < 4 está fora da faixa); 5,0 e 5,5 ficam ambos em ótimo
    assert m["acuracia_faixa"] == pytest.approx(1.0)


def test_comparar_od_tem_os_tres_modelos_e_a_mediana_e_constante():
    validas = _validas()
    treino, teste = validas[validas["grupo"] != "lago_d"], validas[validas["grupo"] == "lago_d"]
    resultado = comparar_od(treino, teste, TILAPIA, n_estimadores=20)
    assert set(resultado) == {"xgboost", "random_forest", "mediana"}
    assert set(resultado["xgboost"]) == {"mae", "rmse", "r2", "acuracia_faixa"}
    esperado = np.mean(np.abs(teste["od"] - np.median(treino["od"])))
    assert resultado["mediana"]["mae"] == pytest.approx(esperado)
    # dados sintéticos com OD função da temperatura: o modelo tem que ganhar do chute
    assert resultado["xgboost"]["mae"] < resultado["mediana"]["mae"]
