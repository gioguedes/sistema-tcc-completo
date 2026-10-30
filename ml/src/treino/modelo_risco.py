"""Previsão de risco para 1, 2 e 3 h: prever pH e temperatura em t+h e aplicar a regra de faixas.

O rótulo é uma função conhecida (faixas.nivel_geral) de pH, temperatura e OD em t+h. Em vez de um
classificador reaprender essa regra (e errar fora do domínio de treino), XGBoost de regressão
preveem a variação de pH e de temperatura até t+h; o OD em t+h sai do estimador de OD aplicado a
esses valores, e o nível sai da própria regra. Variação zero é a persistência, então o modelo só
precisa aprender a dinâmica. O classificador direto fica como linha de base no relatório.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier, XGBRegressor

from src.faixas import CRITICO, FaixaEspecie, nivel_geral
from src.features import BLOCOS_POR_HORA, calcular_features, cobertura, nomes_features
from src.treino.modelo_od import FEATURES_OD
from src.treino.rotulos import HORIZONTES_H, rotular

CLASSES = [0, 1, 2]
GRANDEZAS_DINAMICA = ("ph", "temperatura")
QUANTIS_DINAMICA = {"q10": 0.10, "q90": 0.90}


def montar_dataset_risco(
    series: dict[str, pd.DataFrame], grupo_de: dict[str, str], faixa: FaixaEspecie, cobertura_min_blocos: int
) -> pd.DataFrame:
    """Uma linha por (ponto, bloco) com as 15 variáveis, o nível atual (persistência) e os alvos.

    Cada série precisa das colunas ph, temperatura, od (medido) e od_estimado.
    As variáveis e a persistência usam o OD estimado (o que existe em
    produção); os alvos usam o OD medido. Os alvos da dinâmica são as variações
    de pH e temperatura até t+h (`var_<grandeza>_h<h>`).
    """
    partes = []
    for ponto, serie in series.items():
        entrada = serie[["ph", "temperatura"]].assign(od=serie["od_estimado"])
        parte = calcular_features(entrada, faixa)
        parte["cobertura"] = cobertura(entrada)
        parte["persistencia"] = nivel_geral(entrada["ph"], entrada["temperatura"], entrada["od"], faixa)
        for g in GRANDEZAS_DINAMICA:
            parte[f"{g}_agora"] = serie[g]
        for h in HORIZONTES_H:
            parte[f"alvo_h{h}"] = rotular(serie, faixa, h)
            for g in GRANDEZAS_DINAMICA:
                parte[f"var_{g}_h{h}"] = serie[g].shift(-BLOCOS_POR_HORA * h) - serie[g]
        parte["ponto"] = ponto
        parte["grupo"] = grupo_de[ponto]
        partes.append(parte)

    dataset = pd.concat(partes)
    dataset = dataset[dataset["cobertura"] >= cobertura_min_blocos]
    return dataset.dropna(subset=nomes_features() + ["persistencia"])


def _alvo(dataset: pd.DataFrame, h: int) -> tuple[pd.DataFrame, np.ndarray]:
    validas = dataset.dropna(subset=[f"alvo_h{h}"])
    return validas, validas[f"alvo_h{h}"].to_numpy(dtype=int)


def _regressor(n_estimadores: int, **extras) -> XGBRegressor:
    return XGBRegressor(
        n_estimators=n_estimadores, max_depth=6, learning_rate=0.05, tree_method="hist",
        n_jobs=-1, random_state=42, **extras,
    )


def treinar_risco(dataset: pd.DataFrame, n_estimadores: int = 300) -> dict[int, dict]:
    """Por horizonte e grandeza: XGBoost da variação (centro) e de quantil 10% e 90%."""
    modelos: dict[int, dict] = {}
    for h in HORIZONTES_H:
        modelos[h] = {}
        for g in GRANDEZAS_DINAMICA:
            linhas = dataset.dropna(subset=[f"var_{g}_h{h}"])
            X, y = linhas[nomes_features()], linhas[f"var_{g}_h{h}"]
            modelos[h][g] = {"centro": _regressor(n_estimadores).fit(X, y)}
            for nome, alfa in QUANTIS_DINAMICA.items():
                modelos[h][g][nome] = _regressor(
                    n_estimadores, objective="reg:quantileerror", quantile_alpha=alfa
                ).fit(X, y)
    return modelos


def prever_risco(
    modelos_h: dict, modelo_od, linhas: pd.DataFrame, faixa: FaixaEspecie
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Nível previsto, confiança e valores previstos (ph, temperatura, od) para um horizonte.

    `linhas` tem as 15 variáveis e ph_agora/temperatura_agora. A confiança é a
    fração dos cenários (centro e as 4 combinações dos quantis de 10% e 90% de
    pH e temperatura) que dá o mesmo nível do centro.
    """
    X = linhas[nomes_features()]
    previstos = {
        g: {nome: linhas[f"{g}_agora"].to_numpy() + m.predict(X) for nome, m in modelos_h[g].items()}
        for g in GRANDEZAS_DINAMICA
    }

    def nivel_em(ph: np.ndarray, temperatura: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        od = modelo_od.predict(pd.DataFrame({"temperatura": temperatura, "ph": ph})[FEATURES_OD])
        return nivel_geral(ph, temperatura, od, faixa).astype(int), od

    nivel, od = nivel_em(previstos["ph"]["centro"], previstos["temperatura"]["centro"])
    concordam = np.ones(len(linhas))
    for q_ph in QUANTIS_DINAMICA:
        for q_t in QUANTIS_DINAMICA:
            concordam += nivel_em(previstos["ph"][q_ph], previstos["temperatura"][q_t])[0] == nivel
    valores = {"ph": previstos["ph"]["centro"], "temperatura": previstos["temperatura"]["centro"], "od": od}
    return nivel, concordam / (1 + len(QUANTIS_DINAMICA) ** 2), valores


def treinar_classificador(dataset: pd.DataFrame, n_estimadores: int = 300) -> dict[int, XGBClassifier]:
    """Linha de base: classificador direto do nível em t+h (o modelo de risco até 29/10)."""
    modelos = {}
    for h in HORIZONTES_H:
        linhas, y = _alvo(dataset, h)
        faltando = set(CLASSES) - set(np.unique(y))
        if faltando:
            raise ValueError(f"horizonte {h}h sem exemplos das classes {sorted(faltando)} no treino")
        modelos[h] = XGBClassifier(
            n_estimators=n_estimadores, max_depth=6, learning_rate=0.05, tree_method="hist",
            objective="multi:softprob", n_jobs=-1, random_state=42,
        ).fit(linhas[nomes_features()], y, sample_weight=compute_sample_weight("balanced", y))
    return modelos


def metricas_risco(y_real: np.ndarray, y_previsto: np.ndarray) -> dict:
    return {
        "acuracia": float(accuracy_score(y_real, y_previsto)),
        "f1_macro": float(f1_score(y_real, y_previsto, labels=CLASSES, average="macro", zero_division=0)),
        "recall_critico": float(
            recall_score(y_real, y_previsto, labels=[CRITICO], average="macro", zero_division=0)
        ),
        "matriz_confusao": confusion_matrix(y_real, y_previsto, labels=CLASSES).tolist(),
    }


def avaliar_risco(
    treino: pd.DataFrame, teste: pd.DataFrame, modelo_od, faixa: FaixaEspecie, n_estimadores: int = 300
) -> dict[int, dict]:
    """Por horizonte: previsão + regra (XGBoost), classificador direto e persistência, medidos em `teste`.

    `modelo_od` não pode ter visto os corpos d'água de `teste`.
    """
    dinamica = treinar_risco(treino, n_estimadores)
    classificador = treinar_classificador(treino, n_estimadores)
    resultado = {}
    for h in HORIZONTES_H:
        linhas_teste, y_teste = _alvo(teste, h)
        nivel, _, _ = prever_risco(dinamica[h], modelo_od, linhas_teste, faixa)
        resultado[h] = {
            "xgboost": metricas_risco(y_teste, nivel),
            "classificador": metricas_risco(y_teste, classificador[h].predict(linhas_teste[nomes_features()])),
            "persistencia": metricas_risco(y_teste, linhas_teste["persistencia"].to_numpy(dtype=int)),
            "distribuicao_teste": np.bincount(y_teste, minlength=3).tolist(),
        }
    return resultado
