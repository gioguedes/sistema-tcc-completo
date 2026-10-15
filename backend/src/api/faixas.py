"""Regra de faixas do servico de ML (ml/src/faixas.py, correcao de 30/09), em versao escalar.

A API nao inventa classificacao: o nivel do OD vem pronto do ML (linha h = 0).
Esta regra so classifica o pH e a temperatura da ultima leitura, para compor o
nivel atual do tanque como o `nivel_geral` do ML (pior entre pH, temperatura e OD).
"""

from src.db.models import Especie

NIVEIS = ("otimo", "atencao", "critico")
MARGEM_RELATIVA = 0.10


def _limites(grandeza: str, especie: Especie) -> tuple[float, float]:
    if grandeza == "ph":
        return float(especie.ph_min), float(especie.ph_max)
    if grandeza == "temperatura":
        return float(especie.temp_min), float(especie.temp_max)
    # o OD tem regra propria (sem limite de cima) e chega classificado pelo ML
    raise ValueError(f"grandeza sem classificacao na API: {grandeza}")


def nivel(valor: float, grandeza: str, especie: Especie) -> str:
    minimo, maximo = _limites(grandeza, especie)
    margem = MARGEM_RELATIVA * (maximo - minimo)
    if valor < minimo or valor > maximo:
        return "critico"
    if minimo + margem <= valor <= maximo - margem:
        return "otimo"
    return "atencao"


def pior(*niveis: str) -> str:
    return max(niveis, key=NIVEIS.index)
