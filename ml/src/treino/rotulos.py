import pandas as pd

from src.faixas import FaixaEspecie, nivel_geral
from src.features import BLOCOS_POR_HORA

HORIZONTES_H = (1, 2, 3)


def rotular(serie: pd.DataFrame, faixa: FaixaEspecie, horizonte_h: int) -> pd.Series:
    """Nível real do bloco que começa em t+h, alinhado na linha t.

    Usa ph, temperatura e od (o OD medido). `serie` precisa estar na grade
    regular de 15 min. NaN onde t+h cai fora da série ou num bloco vazio.
    """
    nivel_no_bloco = pd.Series(
        nivel_geral(serie["ph"], serie["temperatura"], serie["od"], faixa), index=serie.index
    )
    return nivel_no_bloco.shift(-BLOCOS_POR_HORA * horizonte_h)
