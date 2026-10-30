from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib

from src.faixas import FaixaEspecie
from src.features import nomes_features

VERSAO_PACOTE = 3


def montar_pacote(
    modelos_od: dict, modelos_risco: dict, faixa_treino: FaixaEspecie, hashes: dict, dominio_od: dict
) -> dict:
    """`dominio_od`: percentis 1 e 99 de temperatura e pH no treino do OD ({grandeza: [p1, p99]})."""
    return {
        "versao": VERSAO_PACOTE,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "features": nomes_features(),
        "faixa_treino": asdict(faixa_treino),
        "hashes_datasets": hashes,
        "dominio_od": dominio_od,
        "od": modelos_od,
        "risco": modelos_risco,
    }


def salvar_pacote(pacote: dict, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pacote, caminho)


def carregar_pacote(caminho: Path) -> dict:
    return joblib.load(caminho)
