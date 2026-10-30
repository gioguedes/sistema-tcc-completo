from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.faixas import NOMES_NIVEL, FaixaEspecie, nivel, parametro_critico
from src.features import calcular_features, cobertura, nomes_features
from src.pacote import VERSAO_PACOTE
from src.treino.modelo_od import FEATURES_OD
from src.treino.modelo_risco import prever_risco
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
    def __init__(self, pacote: dict, cobertura_min_blocos: int, altitude_m: float = 0.0) -> None:
        if pacote.get("versao") != VERSAO_PACOTE:
            raise ValueError(f"pacote de modelos versão {pacote.get('versao')}, esperava {VERSAO_PACOTE}: retreine")
        if pacote["features"] != nomes_features():
            raise ValueError("modelos treinados com variáveis diferentes das de features.py: retreine")
        self._od = pacote["od"]
        # o estimador devolve fração de saturação vezes o OD de saturação na altitude do tanque
        for modelo in self._od.values():
            modelo.altitude_m = altitude_m
        self._dominio = pacote["dominio_od"]
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

    def fora_do_dominio(self, entrada: pd.DataFrame) -> bool:
        """T ou pH fora do que o estimador de OD viu no treino (percentis 1 e 99)."""
        return any(
            not (lo <= float(entrada[g].iloc[0]) <= hi) for g, (lo, hi) in self._dominio.items()
        )

    def _previsao_od(self, atual: pd.Series, faixa: FaixaEspecie, entrada: pd.DataFrame) -> Previsao:
        q10 = float(self._od["od_q10"].predict(entrada)[0])
        q90 = float(self._od["od_q90"].predict(entrada)[0])
        od_min, od_max = faixa.limites("od")
        confianca = float(np.clip(1 - abs(q90 - q10) / (od_max - od_min), 0, 1))
        # fora do domínio os quantis podem ficar estreitos por acaso: o intervalo não vale ali
        if self.fora_do_dominio(entrada):
            confianca = 0.0
        return Previsao(0, "od", float(atual["od"]), NOMES_NIVEL[nivel(atual["od"], "od", faixa)], confianca)

    def _previsoes_risco(self, atual: pd.Series, variaveis: pd.DataFrame, faixa: FaixaEspecie) -> list[Previsao]:
        linhas = variaveis.assign(ph_agora=float(atual["ph"]), temperatura_agora=float(atual["temperatura"]))
        previsoes = []
        for h in HORIZONTES_H:
            niveis_h, confianca, valores = prever_risco(self._risco[h], self._od["od"], linhas, faixa)
            futuros = {g: float(np.clip(valores[g][0], *LIMITES_FISICOS[g])) for g in ("ph", "temperatura", "od")}
            parametro = parametro_critico(futuros, faixa)
            previsoes.append(
                Previsao(
                    horizonte_h=h,
                    parametro_critico=parametro,
                    valor_previsto=futuros[parametro],
                    nivel_risco=NOMES_NIVEL[int(niveis_h[0])],
                    confianca=float(confianca[0]),
                )
            )
        return previsoes
