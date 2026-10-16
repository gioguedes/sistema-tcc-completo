from collections.abc import Callable
from itertools import combinations

import numpy as np
import pandas as pd

FRACAO_TESTE = 0.15
CORTE_TEMPORAL = pd.Timestamp("2024-01-01", tz="UTC")


def linhas_por_grupo(linhas_por_ponto: dict[str, int], grupo_de: dict[str, str]) -> dict[str, int]:
    soma: dict[str, int] = {}
    for ponto, linhas in linhas_por_ponto.items():
        soma[grupo_de[ponto]] = soma.get(grupo_de[ponto], 0) + linhas
    return soma


def escolher_grupos_teste(linhas: dict[str, int], fracao: float = FRACAO_TESTE) -> list[str]:
    """Subconjunto de corpos d'água inteiros cuja soma de linhas fica mais perto de `fracao` do total.

    Busca exaustiva (5 grupos, 31 combinações), então o resultado é
    determinístico sem semente. Empate: menos grupos, depois a lista
    ordenada menor.
    """
    grupos = sorted(linhas)
    if len(grupos) < 2:
        raise ValueError("preciso de pelo menos 2 corpos d'água para separar treino e teste")
    total = sum(linhas.values())

    melhor: tuple[float, int, tuple[str, ...]] | None = None
    for tamanho in range(1, len(grupos)):
        for escolhidos in combinations(grupos, tamanho):
            desvio = abs(sum(linhas[g] for g in escolhidos) / total - fracao)
            chave = (round(desvio, 12), tamanho, escolhidos)
            if melhor is None or chave < melhor:
                melhor = chave
    return list(melhor[2])


def split_temporal(df: pd.DataFrame, corte: pd.Timestamp = CORTE_TEMPORAL) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Treino = blocos antes de `corte` (2023), teste = a partir dele (2024); índice em UTC."""
    return df[df.index < corte], df[df.index >= corte]


def _media(resultados: list):
    """Média de cada número; listas (contagens, matrizes de confusão) são somadas."""
    primeiro = resultados[0]
    if isinstance(primeiro, dict):
        return {chave: _media([r[chave] for r in resultados]) for chave in primeiro}
    if isinstance(primeiro, list):
        return np.sum(resultados, axis=0).tolist()
    return float(np.mean(resultados))


def validacao_cruzada(df: pd.DataFrame, avaliar: Callable[[pd.DataFrame, pd.DataFrame], dict]) -> dict:
    """Deixa um corpo d'água (coluna grupo) de fora por vez: {"por_grupo": {g: resultado}, "media": ...}."""
    por_grupo = {
        str(g): avaliar(df[df["grupo"] != g], df[df["grupo"] == g]) for g in sorted(df["grupo"].unique())
    }
    return {"por_grupo": por_grupo, "media": _media(list(por_grupo.values()))}
