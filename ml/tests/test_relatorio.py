import json

from src.pacote import carregar_pacote
from src.treino.__main__ import treinar
from src.treino.relatorio import gerar_relatorio, veredito_h1, veredito_h2, veredito_h2_tc1
from tests.fabricas import leituras_sinteticas


def _od(mae: float) -> dict:
    return {n: {"mae": mae, "rmse": mae, "r2": 0.0, "acuracia_faixa": 0.5} for n in ("xgboost", "random_forest", "mediana")}


def _risco(acuracia: float, recall_xgb: float, recall_persistencia: float) -> dict:
    def m(acc, rec):
        return {"acuracia": acc, "f1_macro": 0.5, "recall_critico": rec, "matriz_confusao": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}

    return {
        "xgboost": m(acuracia, recall_xgb),
        "random_forest": m(0.5, 0.5),
        "persistencia": m(0.5, recall_persistencia),
        "distribuicao_teste": [1, 1, 1],
    }


def test_h1_exige_mae_ate_0_8():
    assert veredito_h1(_od(0.8)) is True
    assert veredito_h1(_od(0.81)) is False


def test_h2_pelo_criterio_do_tc1_e_so_a_acuracia():
    assert veredito_h2_tc1(_risco(0.80, 0.5, 0.9)) is True
    assert veredito_h2_tc1(_risco(0.79, 0.9, 0.5)) is False


def test_h2_pela_spec_exige_acuracia_e_ganhar_da_persistencia_no_recall_de_critico():
    assert veredito_h2(_risco(0.80, 0.9, 0.8)) is True
    assert veredito_h2(_risco(0.79, 0.9, 0.8)) is False
    # acurácia alta não basta: empatar com a persistência no recall reprova
    assert veredito_h2(_risco(0.99, 0.8, 0.8)) is False


def test_relatorio_escreve_json_e_md_com_os_vereditos(tmp_path):
    validacao_od = {"por_grupo": {"a": _od(1.0), "b": _od(2.0)}, "media": _od(1.5)}
    validacao_risco = {"por_grupo": {"a": {1: _risco(0.7, 0.9, 0.8)}}, "media": {1: _risco(0.7, 0.9, 0.8)}}
    dados = {
        "criado_em": "2026-09-30T00:00:00+00:00",
        "pontos": {"p1": "a", "p2": "a", "p3": "b", "p4": "c"},
        "linhas_por_grupo": {"a": 100, "b": 50, "c": 30},
        "grupos_treino": ["a", "b"],
        "grupos_teste": ["c"],
        "fracao_teste": 30 / 180,
        "distribuicao_niveis": [20, 10, 70],
        "linhas_brutas": 300,
        "linhas_limpas": 200,
        "limpeza": {"nao_aprovado": 40, "temperatura": 50, "ph": 5, "od_faixa": 5},
        "od": {"teste": _od(0.6), "validacao_cruzada": validacao_od, "temporal": _od(0.9)},
        "risco": {"teste": {1: _risco(0.85, 0.9, 0.8)}, "validacao_cruzada": validacao_risco, "temporal": {1: _risco(0.6, 0.5, 0.5)}},
        "hashes_datasets": {"p1/2023-01.rdb": "a" * 64},
    }
    texto = gerar_relatorio(dados, tmp_path).read_text(encoding="utf-8")
    assert "H1: **ATINGIDA**" in texto
    assert "critério do TC1 (acurácia ≥ 80%): **ATINGIDA**" in texto
    assert "no recall de crítico): **ATINGIDA**" in texto
    assert "| a | p1, p2 | 100 |" in texto
    assert "crítico 70.0%" in texto
    assert "| **média** | 1.500 | 1.500 | 1.500 |" in texto
    assert "Split temporal" in texto
    assert json.loads((tmp_path / "relatorio_treino.json").read_text(encoding="utf-8"))["grupos_teste"] == ["c"]


def test_treino_de_ponta_a_ponta_em_dados_sinteticos(tmp_path):
    caminho_modelos = tmp_path / "modelos" / "modelos.joblib"
    caminho_md = treinar(
        leituras_sinteticas(), {"p1/2023-12.rdb": "0" * 64}, caminho_modelos, tmp_path / "relatorios",
        n_estimadores=10,
    )
    pacote = carregar_pacote(caminho_modelos)
    assert set(pacote["risco"]) == {1, 2, 3}
    assert pacote["hashes_datasets"] == {"p1/2023-12.rdb": "0" * 64}

    dados = json.loads((tmp_path / "relatorios" / "relatorio_treino.json").read_text(encoding="utf-8"))
    # lago_a tem 2 pontos (1/3 dos blocos); cada outro lago tem 1/6, o mais perto de 15%
    assert dados["grupos_teste"] == ["lago_b"]
    assert set(dados["grupos_treino"]) | set(dados["grupos_teste"]) == {"lago_a", "lago_b", "lago_c", "lago_d"}
    assert set(dados["od"]["validacao_cruzada"]["por_grupo"]) == set(dados["grupos_treino"])
    assert set(dados["risco"]["temporal"]) == {"1", "2", "3"}
    texto = caminho_md.read_text(encoding="utf-8")
    assert "Validação cruzada por corpo d'água" in texto
    assert "Split temporal (2023 → 2024" in texto
