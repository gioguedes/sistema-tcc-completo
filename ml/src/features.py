import pandas as pd

from src.faixas import GRANDEZAS, FaixaEspecie, normalizar

BLOCO = "15min"
BLOCOS_POR_HORA = 4
# janela em minutos -> quantos blocos de 15 min ela cobre
JANELAS = {30: 2, 60: 4}
BLOCOS_COBERTURA = 4


def para_grade_15min(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Mediana por bloco de 15 min alinhado em :00/:15/:30/:45 UTC, indexada pelo início do bloco.

    `df` tem a coluna ts (UTC). Bloco sem dado fica NaN e nunca é interpolado.
    """
    return df.set_index("ts")[colunas].sort_index().resample(BLOCO).median()


def nomes_features() -> list[str]:
    nomes = []
    for grandeza in GRANDEZAS:
        nomes.append(f"{grandeza}_ultimo")
        nomes.extend(f"{grandeza}_media_{j}" for j in JANELAS)
        nomes.extend(f"{grandeza}_incl_{j}" for j in JANELAS)
    return nomes


def calcular_features(serie: pd.DataFrame, faixa: FaixaEspecie) -> pd.DataFrame:
    """Variáveis em cada bloco t usando só blocos <= t.

    `serie` precisa estar na grade regular de 15 min (NaN nos buracos), com as
    colunas ph, temperatura e od. As janelas contam linhas, por isso a grade
    regular é obrigatória.
    """
    saida = pd.DataFrame(index=serie.index)
    for grandeza in GRANDEZAS:
        z = pd.Series(normalizar(serie[grandeza], grandeza, faixa), index=serie.index)
        saida[f"{grandeza}_ultimo"] = z
        for minutos, blocos in JANELAS.items():
            saida[f"{grandeza}_media_{minutos}"] = z.rolling(blocos, min_periods=blocos * 2 // 3).mean()
        for minutos, blocos in JANELAS.items():
            saida[f"{grandeza}_incl_{minutos}"] = (z - z.shift(blocos)) / (minutos / 60)
    return saida[nomes_features()]


def cobertura(serie: pd.DataFrame) -> pd.Series:
    """Quantos dos últimos 4 blocos têm pH e temperatura ao mesmo tempo."""
    presente = (serie["ph"].notna() & serie["temperatura"].notna()).astype(int)
    return presente.rolling(BLOCOS_COBERTURA, min_periods=1).sum()
