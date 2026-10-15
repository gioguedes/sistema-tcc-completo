import math

import numpy as np
import pytest

from src.faixas import (
    ATENCAO,
    CRITICO,
    OTIMO,
    TILAPIA,
    FaixaEspecie,
    nivel,
    nivel_geral,
    normalizar,
    parametro_critico,
)

# faixa 0-10 em todas as grandezas: margem de 10% = 1,0 exato, sem erro de ponto flutuante
FAIXA_REDONDA = FaixaEspecie(ph_min=0, ph_max=10, temp_min=0, temp_max=10, od_min=0, od_max=10)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (-0.01, CRITICO),
        (0.0, ATENCAO),
        (0.99, ATENCAO),
        (1.0, OTIMO),
        (5.0, OTIMO),
        (9.0, OTIMO),
        (9.01, ATENCAO),
        (10.0, ATENCAO),
        (10.01, CRITICO),
    ],
)
def test_fronteiras_da_faixa(valor, esperado):
    assert nivel(valor, "ph", FAIXA_REDONDA) == esperado
    assert nivel(valor, "temperatura", FAIXA_REDONDA) == esperado


def test_od_abaixo_de_3_e_critico_mesmo_dentro_da_faixa():
    assert nivel(5.0, "od", FAIXA_REDONDA) == OTIMO
    assert nivel(3.0, "od", FAIXA_REDONDA) == OTIMO
    assert nivel(2.99, "od", FAIXA_REDONDA) == CRITICO


def test_od_acima_da_faixa_nao_e_risco():
    # tilápia: OD 4–8 mg/L, margem 0,4; acima de 8 continua ótimo
    assert [nivel(v, "od", TILAPIA) for v in (8.5, 12.0, 20.0)] == [OTIMO, OTIMO, OTIMO]
    assert nivel(4.2, "od", TILAPIA) == ATENCAO
    assert nivel(3.99, "od", TILAPIA) == CRITICO


def test_od_alto_nao_vira_parametro_critico():
    # pH e temperatura no meio da faixa (distância 0,5); OD em 12 mg/L está longe do risco
    ultimos = {"ph": 7.5, "temperatura": 25.0, "od": 12.0}
    assert parametro_critico(ultimos, TILAPIA) == "temperatura"


def test_limiar_absoluto_de_od_nao_vale_para_outras_grandezas():
    assert nivel(2.99, "ph", FAIXA_REDONDA) == OTIMO


def test_tilapia_valores_tipicos():
    assert nivel(7.5, "ph", TILAPIA) == OTIMO
    assert nivel(6.6, "ph", TILAPIA) == ATENCAO
    assert nivel(4.5, "ph", TILAPIA) == CRITICO
    assert nivel(26.0, "temperatura", TILAPIA) == OTIMO
    assert nivel(3.5, "od", TILAPIA) == CRITICO


def test_nivel_geral_e_o_pior_das_tres_grandezas():
    resultado = nivel_geral([5.0, 5.0], [5.0, 0.5], [5.0, 5.0], FAIXA_REDONDA)
    assert list(resultado) == [OTIMO, ATENCAO]

    resultado = nivel_geral([5.0], [0.5], [2.0], FAIXA_REDONDA)
    assert list(resultado) == [CRITICO]


def test_nivel_geral_com_valor_ausente_e_nan():
    resultado = nivel_geral([5.0], [np.nan], [5.0], FAIXA_REDONDA)
    assert math.isnan(resultado[0])


def test_normalizar_leva_a_faixa_para_zero_um():
    assert list(normalizar([6.5, 7.5, 8.5], "ph", TILAPIA)) == [0.0, 0.5, 1.0]


def test_parametro_critico_e_a_grandeza_mais_perto_da_borda():
    ultimos = {"ph": 9.5, "temperatura": 5.0, "od": 5.0}
    assert parametro_critico(ultimos, FAIXA_REDONDA) == "ph"


def test_parametro_critico_fora_da_faixa_vence_quem_esta_na_borda():
    ultimos = {"ph": -2.0, "temperatura": 0.0, "od": 5.0}
    assert parametro_critico(ultimos, FAIXA_REDONDA) == "ph"


def test_parametro_critico_empate_prefere_od_depois_temperatura():
    assert parametro_critico({"ph": 5.0, "temperatura": 5.0, "od": 5.0}, FAIXA_REDONDA) == "od"
    assert parametro_critico({"ph": 2.0, "temperatura": 2.0, "od": 5.0}, FAIXA_REDONDA) == "temperatura"


def test_grandeza_desconhecida_levanta_erro():
    with pytest.raises(ValueError):
        TILAPIA.limites("turbidez")
