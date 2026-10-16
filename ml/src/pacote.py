from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib

from src.faixas import FaixaEspecie
from src.features import nomes_features

VERSAO_PACOTE = 2


def montar_pacote(modelos_od: dict, modelos_risco: dict, faixa_treino: FaixaEspecie, hashes: dict) -> dict:
    return {
        "versao": VERSAO_PACOTE,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "features": nomes_features(),
        "faixa_treino": asdict(faixa_treino),
        "hashes_datasets": hashes,
        "od": modelos_od,
        "risco": modelos_risco,
    }


def salvar_pacote(pacote: dict, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pacote, caminho)


def carregar_pacote(caminho: Path) -> dict:
    return joblib.load(caminho)
