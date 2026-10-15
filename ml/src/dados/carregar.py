import hashlib
from pathlib import Path

import pandas as pd

from src.dados.pontos import CODIGOS_PARAMETRO, PONTOS, Ponto

GRANDEZAS_USGS = ("temperatura", "od", "ph")
# offset do horário local em relação ao UTC, em horas
OFFSETS_H = {"EST": -5, "EDT": -4, "CST": -6, "CDT": -5}


def ler_rdb(caminho: Path, ponto: Ponto) -> pd.DataFrame:
    """Colunas ts (UTC), temperatura, od, ph e o qualificador de cada uma (cd_temperatura, cd_od, cd_ph)."""
    bruto = pd.read_csv(caminho, sep="\t", comment="#", dtype=str, keep_default_na=False)
    # a primeira linha depois do cabeçalho é a de tipos (5s, 15s, 20d...)
    bruto = bruto.iloc[1:].reset_index(drop=True)

    desconhecidos = set(bruto["tz_cd"]) - set(OFFSETS_H)
    if desconhecidos:
        raise ValueError(f"fuso desconhecido em {caminho}: {sorted(desconhecidos)}")
    local = pd.to_datetime(bruto["datetime"], format="%Y-%m-%d %H:%M")
    offset = pd.to_timedelta(bruto["tz_cd"].map(OFFSETS_H), unit="h")
    df = pd.DataFrame({"ts": (local - offset).dt.tz_localize("UTC")})

    for grandeza in GRANDEZAS_USGS:
        coluna = f"{ponto.series[grandeza]}_{CODIGOS_PARAMETRO[grandeza]}"
        if coluna not in bruto.columns:
            raise ValueError(f"{caminho}: coluna {coluna} ({grandeza}) não existe")
        df[grandeza] = pd.to_numeric(bruto[coluna], errors="coerce")
        df[f"cd_{grandeza}"] = bruto[f"{coluna}_cd"]
    return df


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_todos(diretorio: Path, pontos: tuple[Ponto, ...] = PONTOS) -> tuple[pd.DataFrame, dict[str, str]]:
    """Todos os .rdb de todos os pontos, com as colunas ponto e grupo; e o SHA-256 de cada arquivo."""
    partes, hashes = [], {}
    for ponto in pontos:
        arquivos = sorted((diretorio / ponto.codigo).glob("*.rdb"))
        if not arquivos:
            raise FileNotFoundError(
                f"nenhum .rdb em {diretorio / ponto.codigo}: rode python -m src.dados.baixar_usgs"
            )
        for arquivo in arquivos:
            partes.append(ler_rdb(arquivo, ponto).assign(ponto=ponto.codigo, grupo=ponto.grupo))
            hashes[f"{ponto.codigo}/{arquivo.name}"] = sha256(arquivo)
    df = pd.concat(partes, ignore_index=True)
    return df[["ponto", "grupo", "ts", *df.columns.drop(["ponto", "grupo", "ts"])]], hashes
