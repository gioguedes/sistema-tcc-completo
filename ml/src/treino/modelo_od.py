import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from xgboost import XGBRegressor

from src.faixas import FaixaEspecie, niveis

FEATURES_OD = ["temperatura", "ph"]
QUANTIS = {"od_q10": 0.10, "od_q90": 0.90}


def _xgb(n_estimadores: int, **extras) -> XGBRegressor:
    return XGBRegressor(
        n_estimators=n_estimadores, max_depth=6, learning_rate=0.05, tree_method="hist",
        n_jobs=-1, random_state=42, **extras,
    )


def _rf(n_estimadores: int) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=n_estimadores, max_depth=12, min_samples_leaf=20, n_jobs=-1, random_state=42
    )


def treinar_od(treino: pd.DataFrame, n_estimadores: int = 300) -> dict:
    """XGBoost do OD e os dois de quantil (intervalo de 80%); `treino` tem temperatura, ph e od."""
    X, y = treino[FEATURES_OD], treino["od"]
    modelos = {"od": _xgb(n_estimadores).fit(X, y)}
    for nome, alfa in QUANTIS.items():
        modelos[nome] = _xgb(n_estimadores, objective="reg:quantileerror", quantile_alpha=alfa).fit(X, y)
    return modelos


def od_fora_da_dobra(treino: pd.DataFrame, n_estimadores: int = 300) -> np.ndarray:
    """OD estimado para cada linha por um modelo que não viu o corpo d'água (coluna grupo) daquela linha.

    É o que o classificador de risco recebe no treino: um modelo que já viu o
    lago estimaria o OD dele melhor do que vai estimar o do aquário.
    """
    X, y = treino[FEATURES_OD], treino["od"]
    previsto = np.empty(len(treino))
    for dentro, fora in LeaveOneGroupOut().split(X, y, treino["grupo"]):
        modelo = _xgb(n_estimadores).fit(X.iloc[dentro], y.iloc[dentro])
        previsto[fora] = modelo.predict(X.iloc[fora])
    return previsto


def metricas_od(y_real, y_previsto, faixa: FaixaEspecie) -> dict:
    return {
        "mae": float(mean_absolute_error(y_real, y_previsto)),
        "rmse": float(np.sqrt(mean_squared_error(y_real, y_previsto))),
        "r2": float(r2_score(y_real, y_previsto)),
        "acuracia_faixa": float(np.mean(niveis(y_real, "od", faixa) == niveis(y_previsto, "od", faixa))),
    }


def comparar_od(treino: pd.DataFrame, teste: pd.DataFrame, faixa: FaixaEspecie, n_estimadores: int = 300) -> dict:
    """Treina XGBoost, Random Forest e a mediana em `treino` e mede os três em `teste`."""
    X, y = treino[FEATURES_OD], treino["od"]
    previsoes = {
        "xgboost": _xgb(n_estimadores).fit(X, y).predict(teste[FEATURES_OD]),
        "random_forest": _rf(n_estimadores // 3).fit(X, y).predict(teste[FEATURES_OD]),
        "mediana": np.full(len(teste), float(np.median(y))),
    }
    return {nome: metricas_od(teste["od"], p, faixa) for nome, p in previsoes.items()}
