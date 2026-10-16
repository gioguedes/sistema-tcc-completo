import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.faixas import CRITICO, FaixaEspecie, nivel_geral
from src.features import calcular_features, cobertura, nomes_features
from src.treino.rotulos import HORIZONTES_H, rotular

CLASSES = [0, 1, 2]


def montar_dataset_risco(
    series: dict[str, pd.DataFrame], grupo_de: dict[str, str], faixa: FaixaEspecie, cobertura_min_blocos: int
) -> pd.DataFrame:
    """Uma linha por (ponto, bloco) com as 15 variáveis, o nível atual (persistência) e os alvos.

    Cada série precisa das colunas ph, temperatura, od (medido) e od_estimado.
    As variáveis e a persistência usam o OD estimado (o que existe em
    produção); os alvos usam o OD medido.
    """
    partes = []
    for ponto, serie in series.items():
        entrada = serie[["ph", "temperatura"]].assign(od=serie["od_estimado"])
        parte = calcular_features(entrada, faixa)
        parte["cobertura"] = cobertura(entrada)
        parte["persistencia"] = nivel_geral(entrada["ph"], entrada["temperatura"], entrada["od"], faixa)
        for h in HORIZONTES_H:
            parte[f"alvo_h{h}"] = rotular(serie, faixa, h)
        parte["ponto"] = ponto
        parte["grupo"] = grupo_de[ponto]
        partes.append(parte)

    dataset = pd.concat(partes)
    dataset = dataset[dataset["cobertura"] >= cobertura_min_blocos]
    return dataset.dropna(subset=nomes_features() + ["persistencia"])


def _alvo(dataset: pd.DataFrame, h: int) -> tuple[pd.DataFrame, np.ndarray]:
    validas = dataset.dropna(subset=[f"alvo_h{h}"])
    return validas, validas[f"alvo_h{h}"].to_numpy(dtype=int)


def _xgb(n_estimadores: int) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=n_estimadores, max_depth=6, learning_rate=0.05, tree_method="hist",
        objective="multi:softprob", n_jobs=-1, random_state=42,
    )


def _rf(n_estimadores: int) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=n_estimadores, max_depth=12, min_samples_leaf=20,
        class_weight="balanced", n_jobs=-1, random_state=42,
    )


def treinar_risco(dataset: pd.DataFrame, n_estimadores: int = 300) -> dict[int, XGBClassifier]:
    modelos = {}
    for h in HORIZONTES_H:
        linhas, y = _alvo(dataset, h)
        faltando = set(CLASSES) - set(np.unique(y))
        if faltando:
            raise ValueError(f"horizonte {h}h sem exemplos das classes {sorted(faltando)} no treino")
        modelos[h] = _xgb(n_estimadores).fit(
            linhas[nomes_features()], y, sample_weight=compute_sample_weight("balanced", y)
        )
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


def avaliar_risco(treino: pd.DataFrame, teste: pd.DataFrame, n_estimadores: int = 300) -> dict[int, dict]:
    """Por horizonte: XGBoost e Random Forest treinados em `treino` e a persistência, medidos em `teste`."""
    xgb = treinar_risco(treino, n_estimadores)
    resultado = {}
    for h in HORIZONTES_H:
        linhas_treino, y_treino = _alvo(treino, h)
        linhas_teste, y_teste = _alvo(teste, h)
        rf = _rf(n_estimadores // 3).fit(linhas_treino[nomes_features()], y_treino)
        resultado[h] = {
            "xgboost": metricas_risco(y_teste, xgb[h].predict(linhas_teste[nomes_features()])),
            "random_forest": metricas_risco(y_teste, rf.predict(linhas_teste[nomes_features()])),
            "persistencia": metricas_risco(y_teste, linhas_teste["persistencia"].to_numpy(dtype=int)),
            "distribuicao_teste": np.bincount(y_teste, minlength=3).tolist(),
        }
    return resultado
