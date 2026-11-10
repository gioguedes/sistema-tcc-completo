"""Medidas complementares dos modelos já treinados. Não retreina nem regrava o pacote de modelos.

Uso, na pasta ml/ e com o mesmo .env do treino:  python -m analises.medidas_complementares

Grava relatorios/medidas_complementares.json com o que o relatório de treino não tem:
- linhas de base do estimador de OD (fração de saturação constante e XGBoost só com temperatura),
  no teste final e na validação cruzada por corpo d'água;
- episódios de OD baixo no teste final;
- cobertura do intervalo de quantis e a confiança que sai dele, fora da dobra e no teste final;
- previsão de risco nas mudanças de nível e como aviso antecipado de nível crítico.
"""

import json
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.model_selection import LeaveOneGroupOut
from xgboost import XGBRegressor

from src.config import Settings
from src.dados.carregar import carregar_todos
from src.dados.limpar import limpar
from src.faixas import CRITICO, TILAPIA, FaixaEspecie, nivel_geral, niveis
from src.oxigenio import od_saturacao
from src.pacote import carregar_pacote
from src.treino.modelo_od import FEATURES_OD, MONOTONIA, treinar_od
from src.treino.modelo_risco import montar_dataset_risco, prever_risco
from src.treino.preparar import grupos_dos_pontos, linhas_validas_od, series_por_ponto
from src.treino.rotulos import HORIZONTES_H
from src.treino.split import escolher_grupos_teste, linhas_por_grupo

logger = logging.getLogger(__name__)

N_ESTIMADORES = 300
# o limiar de baixa confiança é o quartil inferior da confiança em corpos d'água não vistos
PERCENTIL_LIMIAR = 25


def _mae(real, previsto) -> float:
    return float(np.mean(np.abs(np.asarray(real) - np.asarray(previsto))))


def confianca_do_intervalo(q10, q90, faixa: FaixaEspecie) -> np.ndarray:
    """Mesma conta de src.servico.inferencia: 1 menos a largura do intervalo sobre a largura da faixa de OD."""
    return np.clip(1 - np.abs(np.asarray(q90) - np.asarray(q10)) / (faixa.od_max - faixa.od_min), 0, 1)


def _xgb_so_temperatura(treino: pd.DataFrame) -> XGBRegressor:
    modelo = XGBRegressor(
        n_estimators=N_ESTIMADORES, max_depth=6, learning_rate=0.05, tree_method="hist",
        n_jobs=-1, random_state=42, monotone_constraints="(-1)",
    )
    return modelo.fit(treino[["temperatura"]], treino["od"] / od_saturacao(treino["temperatura"]))


def _xgb_temperatura_e_ph(treino: pd.DataFrame) -> XGBRegressor:
    modelo = XGBRegressor(
        n_estimators=N_ESTIMADORES, max_depth=6, learning_rate=0.05, tree_method="hist",
        n_jobs=-1, random_state=42, monotone_constraints=MONOTONIA,
    )
    return modelo.fit(treino[FEATURES_OD], treino["od"] / od_saturacao(treino["temperatura"]))


def linhas_de_base_od(treino: pd.DataFrame, teste: pd.DataFrame) -> dict:
    """MAE (mg/L) em `teste` da mediana, da fração de saturação constante, do XGBoost só com T e do com T e pH."""
    saturacao = od_saturacao(teste["temperatura"])
    fracao = float(np.median(treino["od"] / od_saturacao(treino["temperatura"])))
    return {
        "mediana": _mae(teste["od"], np.full(len(teste), np.median(treino["od"]))),
        "fracao_constante_da_saturacao": _mae(teste["od"], fracao * saturacao),
        "xgboost_so_temperatura": _mae(teste["od"], _xgb_so_temperatura(treino).predict(teste[["temperatura"]]) * saturacao),
        "xgboost_temperatura_e_ph": _mae(teste["od"], _xgb_temperatura_e_ph(treino).predict(teste[FEATURES_OD]) * saturacao),
        "fracao_mediana_do_treino": fracao,
    }


def od_baixo(real: np.ndarray, estimado: np.ndarray, saturacao: np.ndarray, faixa: FaixaEspecie) -> dict:
    nivel_estimado = niveis(estimado, "od", faixa)
    abaixo_minimo, abaixo_5 = real < faixa.od_min, real < 5.0
    return {
        "blocos_com_od_abaixo_do_minimo": int(abaixo_minimo.sum()),
        "desses_estimados_fora_do_otimo": int((nivel_estimado[abaixo_minimo] > 0).sum()),
        "desses_estimados_como_critico": int((nivel_estimado[abaixo_minimo] == CRITICO).sum()),
        "menor_estimativa": float(estimado.min()),
        "menor_valor_medido": float(real.min()),
        "blocos_com_od_abaixo_de_5": int(abaixo_5.sum()),
        "vies_com_od_abaixo_de_5": float(np.mean(estimado[abaixo_5] - real[abaixo_5])),
        "fracao_das_estimativas_acima_da_saturacao": float((estimado > saturacao).mean()),
        "fracao_dos_valores_medidos_acima_da_saturacao": float((real > saturacao).mean()),
        "maior_fracao_de_saturacao_estimada": float((estimado / saturacao).max()),
    }


def confianca_fora_da_dobra(treino: pd.DataFrame, faixa: FaixaEspecie) -> pd.DataFrame:
    """Estimativa, quantis e confiança de cada linha por modelos que não viram o corpo d'água dela."""
    saida = pd.DataFrame(index=np.arange(len(treino)), columns=["estimado", "q10", "q90"], dtype=float)
    for dentro, fora in LeaveOneGroupOut().split(treino, groups=treino["grupo"]):
        modelos = treinar_od(treino.iloc[dentro], N_ESTIMADORES)
        saida.loc[fora, "estimado"] = modelos["od"].predict(treino.iloc[fora])
        saida.loc[fora, "q10"] = modelos["od_q10"].predict(treino.iloc[fora])
        saida.loc[fora, "q90"] = modelos["od_q90"].predict(treino.iloc[fora])
    saida["real"] = treino["od"].to_numpy()
    saida["confianca"] = confianca_do_intervalo(saida["q10"], saida["q90"], faixa)
    return saida


def resumo_confianca(real, estimado, q10, q90, faixa: FaixaEspecie, limiar: float) -> dict:
    real, estimado = np.asarray(real, dtype=float), np.asarray(estimado, dtype=float)
    confianca = confianca_do_intervalo(q10, q90, faixa)
    baixa = confianca < limiar
    return {
        "cobertura_do_intervalo_nominal_80": float(((real >= np.asarray(q10)) & (real <= np.asarray(q90))).mean()),
        "largura_media_do_intervalo": float(np.mean(np.asarray(q90) - np.asarray(q10))),
        "percentis_da_confianca": {f"p{p}": float(np.percentile(confianca, p)) for p in (5, 10, 25, 50, 75, 90)},
        "fracao_com_confianca_a_partir_de_0_5": float((confianca >= 0.5).mean()),
        "limiar": limiar,
        "fracao_abaixo_do_limiar": float(baixa.mean()),
        "mae_abaixo_do_limiar": _mae(real[baixa], estimado[baixa]) if baixa.any() else None,
        "mae_a_partir_do_limiar": _mae(real[~baixa], estimado[~baixa]) if (~baixa).any() else None,
    }


def risco_nas_mudancas(serie: pd.DataFrame, dataset: pd.DataFrame, pacote: dict, faixa: FaixaEspecie) -> dict:
    """Por horizonte: acerto nas mudanças de nível e o modelo como aviso antecipado de nível crítico."""
    nivel_agora = pd.Series(nivel_geral(serie["ph"], serie["temperatura"], serie["od"], faixa), index=serie.index)
    saida = {}
    for h in HORIZONTES_H:
        linhas = dataset.dropna(subset=[f"alvo_h{h}"])
        real = linhas[f"alvo_h{h}"].to_numpy(dtype=int)
        previsto, _, _ = prever_risco(pacote["risco"][h], pacote["od"]["od"], linhas, faixa)
        persistencia = linhas["persistencia"].to_numpy(dtype=int)
        agora = nivel_agora.reindex(linhas.index).to_numpy()
        mudou = ~np.isnan(agora) & (real != agora)
        # aviso antecipado: o sistema ainda não vê crítico (persistência) e o modelo prevê crítico em t+h
        sem_critico_agora = persistencia != CRITICO
        entradas = sem_critico_agora & (real == CRITICO)
        avisos = sem_critico_agora & (previsto == CRITICO)
        saidas_previstas = (persistencia == CRITICO) & (previsto != CRITICO)
        saida[h] = {
            "blocos": int(len(real)),
            "acuracia_modelo": float((previsto == real).mean()),
            "acuracia_persistencia": float((persistencia == real).mean()),
            "mudancas_de_nivel": int(mudou.sum()),
            "acerto_do_modelo_nas_mudancas": float((previsto[mudou] == real[mudou]).mean()),
            "acerto_da_persistencia_nas_mudancas": float((persistencia[mudou] == real[mudou]).mean()),
            "entradas_em_critico": int(entradas.sum()),
            "avisos_antecipados": int(avisos.sum()),
            "avisos_confirmados": int((avisos & entradas).sum()),
            "captura_das_entradas": float((avisos & entradas).sum() / max(entradas.sum(), 1)),
            "precisao_dos_avisos": float((avisos & entradas).sum() / max(avisos.sum(), 1)),
            "saidas_do_critico_previstas": int(saidas_previstas.sum()),
            "saidas_previstas_nao_confirmadas": int((saidas_previstas & (real == CRITICO)).sum()),
        }
    return saida


def medir(bruto: pd.DataFrame, pacote: dict, cobertura_min_blocos: int = 3) -> dict:
    limpo, _ = limpar(bruto)
    series = series_por_ponto(limpo)
    grupo_de = grupos_dos_pontos(limpo)
    validas = pd.concat(linhas_validas_od(s).assign(ponto=p, grupo=grupo_de[p]) for p, s in series.items())
    grupos_teste = escolher_grupos_teste(linhas_por_grupo(validas.groupby("ponto").size().to_dict(), grupo_de))
    treino = validas[~validas["grupo"].isin(grupos_teste)]
    teste = validas[validas["grupo"].isin(grupos_teste)]
    logger.info("teste: %s (%d blocos) | treino: %d blocos", grupos_teste, len(teste), len(treino))

    real = teste["od"].to_numpy()
    estimado = pacote["od"]["od"].predict(teste[FEATURES_OD])
    q10 = pacote["od"]["od_q10"].predict(teste[FEATURES_OD])
    q90 = pacote["od"]["od_q90"].predict(teste[FEATURES_OD])
    saturacao = od_saturacao(teste["temperatura"])

    validacao = {
        g: linhas_de_base_od(treino[treino["grupo"] != g], treino[treino["grupo"] == g])
        for g in sorted(treino["grupo"].unique())
    }
    validacao["media"] = {k: float(np.mean([v[k] for v in validacao.values()])) for k in next(iter(validacao.values()))}
    logger.info("linhas de base do OD prontas")

    fora = confianca_fora_da_dobra(treino, TILAPIA)
    limiar = float(np.floor(np.percentile(fora["confianca"], PERCENTIL_LIMIAR) * 100) / 100)
    logger.info("limiar de confiança (percentil %d fora da dobra): %.2f", PERCENTIL_LIMIAR, limiar)

    resultado = {
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "pacote_criado_em": pacote["criado_em"],
        "grupos_teste": grupos_teste,
        "od_teste": {
            "mae_do_pacote": _mae(real, estimado),
            "linhas_de_base": linhas_de_base_od(treino, teste),
            "od_baixo": od_baixo(real, estimado, saturacao, TILAPIA),
        },
        "od_validacao_cruzada": validacao,
        "confianca": {
            "percentil_do_limiar": PERCENTIL_LIMIAR,
            "limiar": limiar,
            "fora_da_dobra": resumo_confianca(fora["real"], fora["estimado"], fora["q10"], fora["q90"], TILAPIA, limiar),
            "teste": resumo_confianca(real, estimado, q10, q90, TILAPIA, limiar),
        },
    }

    risco = {}
    for ponto, serie in series.items():
        if grupo_de[ponto] not in grupos_teste:
            continue
        serie = serie.copy()
        serie["od_estimado"] = np.nan
        linhas = linhas_validas_od(serie).index
        serie.loc[linhas, "od_estimado"] = pacote["od"]["od"].predict(serie.loc[linhas, FEATURES_OD])
        dataset = montar_dataset_risco({ponto: serie}, grupo_de, TILAPIA, cobertura_min_blocos)
        risco[ponto] = risco_nas_mudancas(serie, dataset, pacote, TILAPIA)
    resultado["risco_teste"] = risco
    return resultado


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    bruto, _ = carregar_todos(settings.ml_datasets_dir / "usgs")
    resultado = medir(bruto, carregar_pacote(settings.caminho_modelos), settings.ml_cobertura_min_blocos)
    caminho = settings.ml_relatorios_dir / "medidas_complementares.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("medidas complementares em %s", caminho)


if __name__ == "__main__":
    main()
