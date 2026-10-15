from dataclasses import dataclass

import numpy as np

OTIMO, ATENCAO, CRITICO = 0, 1, 2
NOMES_NIVEL = ("otimo", "atencao", "critico")
GRANDEZAS = ("ph", "temperatura", "od")
MARGEM_RELATIVA = 0.10
OD_CRITICO_ABSOLUTO = 3.0

# ordem de desempate do parametro_critico: o primeiro vence
PRIORIDADE_DESEMPATE = ("od", "temperatura", "ph")


@dataclass(frozen=True)
class FaixaEspecie:
    ph_min: float
    ph_max: float
    temp_min: float
    temp_max: float
    od_min: float
    od_max: float

    def limites(self, grandeza: str) -> tuple[float, float]:
        if grandeza == "ph":
            return self.ph_min, self.ph_max
        if grandeza == "temperatura":
            return self.temp_min, self.temp_max
        if grandeza == "od":
            return self.od_min, self.od_max
        raise ValueError(f"grandeza desconhecida: {grandeza}")


TILAPIA = FaixaEspecie(ph_min=6.5, ph_max=8.5, temp_min=20.0, temp_max=30.0, od_min=4.0, od_max=8.0)


def normalizar(valores, grandeza: str, faixa: FaixaEspecie) -> np.ndarray:
    minimo, maximo = faixa.limites(grandeza)
    return (np.asarray(valores, dtype=float) - minimo) / (maximo - minimo)


def niveis(valores, grandeza: str, faixa: FaixaEspecie) -> np.ndarray:
    """Nível por valor (0, 1, 2); NaN onde o valor é NaN."""
    v = np.asarray(valores, dtype=float)
    minimo, maximo = faixa.limites(grandeza)
    margem = MARGEM_RELATIVA * (maximo - minimo)

    resultado = np.full(v.shape, float(ATENCAO))
    if grandeza == "od":
        # OD alto não é risco para o peixe: o perigo é a hipóxia. O excesso só
        # importa como supersaturação de gases, que pede sensor de pressão total
        resultado[v >= minimo + margem] = OTIMO
        resultado[(v < minimo) | (v < OD_CRITICO_ABSOLUTO)] = CRITICO
    else:
        resultado[(v >= minimo + margem) & (v <= maximo - margem)] = OTIMO
        resultado[(v < minimo) | (v > maximo)] = CRITICO
    resultado[np.isnan(v)] = np.nan
    return resultado


def nivel(valor: float, grandeza: str, faixa: FaixaEspecie) -> int:
    return int(niveis([valor], grandeza, faixa)[0])


def nivel_geral(ph, temperatura, od, faixa: FaixaEspecie) -> np.ndarray:
    """Pior nível entre as três grandezas; NaN se qualquer uma for NaN."""
    return np.maximum.reduce(
        [niveis(ph, "ph", faixa), niveis(temperatura, "temperatura", faixa), niveis(od, "od", faixa)]
    )


def parametro_critico(ultimos: dict[str, float], faixa: FaixaEspecie) -> str:
    """Grandeza mais perto de sair da faixa (distância normalizada à borda de risco mais próxima).

    Para o OD só a borda de baixo conta, porque OD alto não é risco.
    """

    def distancia(grandeza: str) -> float:
        z = float(normalizar(ultimos[grandeza], grandeza, faixa))
        return z if grandeza == "od" else min(z, 1.0 - z)

    return min(PRIORIDADE_DESEMPATE, key=distancia)
