import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from xgboost import XGBRegressor

from src.faixas import FaixaEspecie, niveis
from src.oxigenio import od_saturacao

FEATURES_OD = ["temperatura", "ph"]
QUANTIS = {"od_q10": 0.10, "od_q90": 0.90}
# OD cai com a temperatura e sobe com o pH (fotossíntese consome CO2): restrição monotônica
MONOTONIA = "(-1,1)"


class EstimadorOD:
    """XGBoost que estima a fração de saturação OD/OD_sat(T) e devolve OD em mg/L.

    Separa a física (solubilidade, que depende da temperatura e da pressão) da
    biologia, e corrige a altitude: os lagos do USGS estão perto do nível do mar,
    e o tanque pode não estar. `altitude_m` é ajustada pelo serviço.
    """

    def __init__(self, modelo: XGBRegressor, altitude_m: float = 0.0) -> None:
        self.modelo = modelo
        self.altitude_m = altitude_m

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        fracao = self.modelo.predict(X[FEATURES_OD])
        return fracao * od_saturacao(X["temperatura"], self.altitude_m)


def _xgb(n_estimadores: int, **extras) -> XGBRegressor:
    return XGBRegressor(
        n_estimators=n_estimadores, max_depth=6, learning_rate=0.05, tree_method="hist",
        n_jobs=-1, random_state=42, **extras,
    )


def _rf(n_estimadores: int) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=n_estimadores, max_depth=12, min_samples_leaf=20, n_jobs=-1, random_state=42
    )


def _ajustar(treino: pd.DataFrame, n_estimadores: int, **extras) -> EstimadorOD:
    # os lagos de treino ficam perto do nível do mar: a saturação deles é a de 1 atm
    fracao = treino["od"] / od_saturacao(treino["temperatura"])
    modelo = _xgb(n_estimadores, monotone_constraints=MONOTONIA, **extras).fit(treino[FEATURES_OD], fracao)
    return EstimadorOD(modelo)


def treinar_od_central(treino: pd.DataFrame, n_estimadores: int = 300) -> EstimadorOD:
    return _ajustar(treino, n_estimadores)


def treinar_od(treino: pd.DataFrame, n_estimadores: int = 300) -> dict:
    """Estimador do OD e os dois de quantil (intervalo de 80%); `treino` tem temperatura, ph e od."""
    modelos = {"od": treinar_od_central(treino, n_estimadores)}
    for nome, alfa in QUANTIS.items():
        modelos[nome] = _ajustar(treino, n_estimadores, objective="reg:quantileerror", quantile_alpha=alfa)
    return modelos


def od_fora_da_dobra(treino: pd.DataFrame, n_estimadores: int = 300) -> np.ndarray:
    """OD estimado para cada linha por um modelo que não viu o corpo d'água (coluna grupo) daquela linha.

    É o que o classificador de risco recebe no treino: um modelo que já viu o
    lago estimaria o OD dele melhor do que vai estimar o do aquário.
    """
    previsto = np.empty(len(treino))
    for dentro, fora in LeaveOneGroupOut().split(treino, groups=treino["grupo"]):
        modelo = treinar_od_central(treino.iloc[dentro], n_estimadores)
        previsto[fora] = modelo.predict(treino.iloc[fora])
    return previsto


def metricas_od(y_real, y_previsto, faixa: FaixaEspecie) -> dict:
    return {
        "mae": float(mean_absolute_error(y_real, y_previsto)),
        "rmse": float(np.sqrt(mean_squared_error(y_real, y_previsto))),
        "r2": float(r2_score(y_real, y_previsto)),
        "acuracia_faixa": float(np.mean(niveis(y_real, "od", faixa) == niveis(y_previsto, "od", faixa))),
    }


def comparar_od(treino: pd.DataFrame, teste: pd.DataFrame, faixa: FaixaEspecie, n_estimadores: int = 300) -> dict:
    """Treina o estimador (XGBoost), Random Forest e a mediana em `treino` e mede os três em `teste`."""
    X, y = treino[FEATURES_OD], treino["od"]
    previsoes = {
        "xgboost": treinar_od_central(treino, n_estimadores).predict(teste),
        "random_forest": _rf(n_estimadores // 3).fit(X, y).predict(teste[FEATURES_OD]),
        "mediana": np.full(len(teste), float(np.median(y))),
    }
    return {nome: metricas_od(teste["od"], p, faixa) for nome, p in previsoes.items()}
