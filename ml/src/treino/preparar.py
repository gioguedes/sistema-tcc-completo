import pandas as pd

from src.features import para_grade_15min


def series_por_ponto(df_limpo: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Uma grade de 15 min por ponto com temperatura, ph e od (o OD medido, alvo do estimador)."""
    return {
        str(ponto): para_grade_15min(grupo, ["temperatura", "ph", "od"])
        for ponto, grupo in df_limpo.groupby("ponto")
    }


def grupos_dos_pontos(df_limpo: pd.DataFrame) -> dict[str, str]:
    return {str(p): str(g) for p, g in df_limpo.groupby("ponto")["grupo"].first().items()}


def linhas_validas_od(serie: pd.DataFrame) -> pd.DataFrame:
    return serie.dropna(subset=["temperatura", "ph", "od"])
