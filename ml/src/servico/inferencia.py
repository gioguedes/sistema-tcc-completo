from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.faixas import NOMES_NIVEL, FaixaEspecie, nivel, parametro_critico
from src.features import calcular_features, cobertura, nomes_features
from src.pacote import VERSAO_PACOTE
from src.treino.modelo_od import FEATURES_OD
from src.treino.rotulos import HORIZONTES_H

ATRASO_MAX = timedelta(minutes=30)
# a projeção linear não pode sair do que é fisicamente possível (mesmos limites dos CHECKs de especies)
LIMITES_FISICOS = {"ph": (0.0, 14.0), "temperatura": (0.0, 50.0), "od": (0.0, 20.0)}


@dataclass(frozen=True)
class Previsao:
    horizonte_h: int
    parametro_critico: str
    valor_previsto: float
    nivel_risco: str
    confianca: float


class Inferencia:
    def __init__(self, pacote: dict, cobertura_min_blocos: int) -> None:
        if pacote.get("versao") != VERSAO_PACOTE:
            raise ValueError(f"pacote de modelos versão {pacote.get('versao')}, esperava {VERSAO_PACOTE}: retreine")
        if pacote["features"] != nomes_features():
            raise ValueError("modelos treinados com variáveis diferentes das de features.py: retreine")
        self._od = pacote["od"]
        self._risco = pacote["risco"]
        self._cobertura_min = cobertura_min_blocos

    def prever(self, janela: pd.DataFrame, faixa: FaixaEspecie, agora: datetime) -> list[Previsao] | None:
        """4 previsões (h = 0..3) ou None quando os dados não bastam (indeterminado, UC06).

        `janela` é a grade de 15 min de `ler_janela` (colunas ph e temperatura).
        """
        completas = janela["ph"].notna() & janela["temperatura"].notna()
        if not completas.any():
            return None
        ultimo = janela.index[completas][-1]
        if pd.Timestamp(agora) - ultimo > ATRASO_MAX:
            return None
        # o bloco corrente pode ainda não ter leitura; a janela termina no último bloco completo
        janela, completas = janela.loc[:ultimo], completas.loc[:ultimo]
        if cobertura(janela).iloc[-1] < self._cobertura_min:
            return None

        entrada_od = janela.loc[completas, FEATURES_OD]
        serie = janela[["ph", "temperatura"]].assign(od=np.nan)
        serie.loc[entrada_od.index, "od"] = self._od["od"].predict(entrada_od)
        variaveis = calcular_features(serie, faixa).iloc[[-1]]
        if variaveis.isna().any(axis=None):
            return None

        atual = serie.iloc[-1]
        return [self._previsao_od(atual, faixa, entrada_od.iloc[[-1]])] + self._previsoes_risco(
            atual, variaveis, faixa
        )

    def _previsao_od(self, atual: pd.Series, faixa: FaixaEspecie, entrada: pd.DataFrame) -> Previsao:
        q10 = float(self._od["od_q10"].predict(entrada)[0])
        q90 = float(self._od["od_q90"].predict(entrada)[0])
        od_min, od_max = faixa.limites("od")
        confianca = float(np.clip(1 - abs(q90 - q10) / (od_max - od_min), 0, 1))
        return Previsao(0, "od", float(atual["od"]), NOMES_NIVEL[nivel(atual["od"], "od", faixa)], confianca)

    def _previsoes_risco(self, atual: pd.Series, variaveis: pd.DataFrame, faixa: FaixaEspecie) -> list[Previsao]:
        ultimos = {g: float(atual[g]) for g in ("ph", "temperatura", "od")}
        parametro = parametro_critico(ultimos, faixa)
        minimo, maximo = faixa.limites(parametro)
        # inclinação de 60 min volta da escala normalizada para a unidade da grandeza (por hora)
        inclinacao = float(variaveis[f"{parametro}_incl_60"].iloc[0]) * (maximo - minimo)

        previsoes = []
        for h in HORIZONTES_H:
            probabilidades = self._risco[h].predict_proba(variaveis)[0]
            classe = int(np.argmax(probabilidades))
            previsoes.append(
                Previsao(
                    horizonte_h=h,
                    parametro_critico=parametro,
                    valor_previsto=float(np.clip(ultimos[parametro] + inclinacao * h, *LIMITES_FISICOS[parametro])),
                    nivel_risco=NOMES_NIVEL[classe],
                    confianca=float(probabilidades[classe]),
                )
            )
        return previsoes
