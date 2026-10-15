import pandas as pd

QUALIFICADORES = ["cd_temperatura", "cd_od", "cd_ph"]


def _aprovado(df: pd.DataFrame) -> pd.Series:
    # "A" é Approved; o USGS às vezes acrescenta sufixo ("A:e" = aprovado, estimado)
    return df[QUALIFICADORES].apply(lambda c: c.fillna("").str.startswith("A")).all(axis=1)


REGRAS = (
    ("nao_aprovado", _aprovado),
    ("temperatura", lambda df: df["temperatura"].between(15, 35)),
    ("ph", lambda df: df["ph"].between(4, 10)),
    ("od_faixa", lambda df: df["od"].between(0, 20)),
)


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Aplica as regras em ordem; devolve o que sobrou (sem os qualificadores) e quantas linhas cada regra removeu."""
    removidas: dict[str, int] = {}
    for nome, mantem in REGRAS:
        mascara = mantem(df)
        removidas[nome] = int((~mascara).sum())
        df = df[mascara]
    return df.drop(columns=QUALIFICADORES).reset_index(drop=True), removidas
