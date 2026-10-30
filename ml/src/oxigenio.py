"""OD de saturação em água doce: Benson e Krause (1984), na forma do APHA 4500-O e do memorando
USGS OWQ 2011.03, com a correção de pressão pela altitude. A mesma fórmula está no painel
(dashboard/src/dominio/oxigenio.ts)."""

import numpy as np


def pressao_atm(altitude_m: float) -> float:
    """Pressão barométrica (atm) da atmosfera padrão na altitude dada."""
    return (1 - 2.25577e-5 * altitude_m) ** 5.25588


def od_saturacao(temperatura_c, altitude_m: float = 0.0) -> np.ndarray:
    t_c = np.asarray(temperatura_c, dtype=float)
    t = t_c + 273.15
    ln_1atm = -139.34411 + 1.575701e5 / t - 6.642308e7 / t**2 + 1.2438e10 / t**3 - 8.621949e11 / t**4
    p = pressao_atm(altitude_m)
    vapor = np.exp(11.8571 - 3840.7 / t - 216961 / t**2)
    theta = 0.000975 - 1.426e-5 * t_c + 6.436e-8 * t_c**2
    return np.exp(ln_1atm) * p * ((1 - vapor / p) * (1 - theta * p)) / ((1 - vapor) * (1 - theta))
