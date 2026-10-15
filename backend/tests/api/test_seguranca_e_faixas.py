from datetime import timedelta

import pytest

from src.api import faixas
from src.api.seguranca import ACESSO, RENOVACAO, emitir_token, gerar_hash_senha, ler_token, verificar_senha
from src.db.models import Especie

SEGREDO = "s" * 48
TILAPIA = Especie(ph_min=6.5, ph_max=8.5, temp_min=20.0, temp_max=30.0, od_min=4.0, od_max=8.0)


def test_hash_de_senha_confere_so_com_a_senha_certa():
    senha_hash = gerar_hash_senha("correta-123")
    assert senha_hash.startswith("scrypt$")
    assert verificar_senha("correta-123", senha_hash)
    assert not verificar_senha("errada-123", senha_hash)
    assert gerar_hash_senha("correta-123") != senha_hash  # sal aleatorio


def test_hash_fora_do_formato_nunca_confere():
    # o seed grava um texto fixo no lugar do hash: esse usuario ainda nao tem senha
    assert not verificar_senha("sem-autenticacao-neste-sub-projeto", "sem-autenticacao-neste-sub-projeto")


def test_token_so_vale_para_o_proprio_tipo_e_dentro_da_validade():
    acesso, _ = emitir_token(7, ACESSO, timedelta(minutes=5), SEGREDO)
    assert ler_token(acesso, ACESSO, SEGREDO)["sub"] == "7"
    assert ler_token(acesso, RENOVACAO, SEGREDO) is None
    assert ler_token(acesso, ACESSO, "o" * 48) is None

    expirado, _ = emitir_token(7, ACESSO, timedelta(seconds=-1), SEGREDO)
    assert ler_token(expirado, ACESSO, SEGREDO) is None


@pytest.mark.parametrize(
    ("valor", "grandeza", "esperado"),
    [
        # tilapia: pH 6,5-8,5 (margem 0,2) e temperatura 20-30 (margem 1,0), como no ml/src/faixas.py
        (7.5, "ph", "otimo"),
        (6.7, "ph", "otimo"),
        (6.6, "ph", "atencao"),
        (8.4, "ph", "atencao"),
        (6.4, "ph", "critico"),
        (8.6, "ph", "critico"),
        (25.0, "temperatura", "otimo"),
        (20.5, "temperatura", "atencao"),
        (31.0, "temperatura", "critico"),
    ],
)
def test_nivel_segue_a_regra_de_faixas_do_ml(valor, grandeza, esperado):
    assert faixas.nivel(valor, grandeza, TILAPIA) == esperado


def test_od_nao_e_classificado_pela_api():
    with pytest.raises(ValueError):
        faixas.nivel(5.0, "od", TILAPIA)


def test_pior_nivel():
    assert faixas.pior("otimo", "critico", "atencao") == "critico"
    assert faixas.pior("otimo", "atencao") == "atencao"
    assert faixas.pior("otimo") == "otimo"
