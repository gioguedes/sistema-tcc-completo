import numpy as np
import pandas as pd

from src.faixas import TILAPIA
from src.pacote import montar_pacote
from src.treino.modelo_od import FEATURES_OD, treinar_od
from src.treino.modelo_risco import montar_dataset_risco, treinar_risco
from src.treino.preparar import grupos_dos_pontos, linhas_validas_od, series_por_ponto

# dois pontos no mesmo lago, como os três do Lake Houston
PONTOS_SINTETICOS = {"p1": "lago_a", "p2": "lago_a", "p3": "lago_b", "p4": "lago_c", "p5": "lago_d"}


def leituras_sinteticas(
    pontos: dict[str, str] = PONTOS_SINTETICOS, inicio: str = "2023-12-25", dias: int = 14, semente: int = 0
) -> pd.DataFrame:
    """Linhas no formato de carregar_todos, a cada 15 min: ciclo diário que cruza as bordas da tilápia.

    O início em 25/12 deixa metade dos dias em 2023 e metade em 2024, para o
    split temporal ter treino e teste.
    """
    gerador = np.random.default_rng(semente)
    blocos = dias * 96
    partes = []
    for i, (ponto, grupo) in enumerate(pontos.items()):
        fase = 2 * np.pi * np.arange(blocos) / 96 + i
        temperatura = 25 + 4 * np.sin(fase) + gerador.normal(0, 0.1, blocos)
        ph = 7.5 + 1.6 * np.sin(fase + 1.0) + gerador.normal(0, 0.05, blocos)
        od = np.clip(13.0 - 0.3 * temperatura + 1.5 * np.sin(fase + 2.0), 0.5, 9.0)
        partes.append(
            pd.DataFrame(
                {
                    "ponto": ponto,
                    "grupo": grupo,
                    "ts": pd.date_range(inicio, periods=blocos, freq="15min", tz="UTC"),
                    "temperatura": temperatura,
                    "cd_temperatura": "A",
                    "od": od,
                    "cd_od": "A",
                    "ph": ph,
                    "cd_ph": "A",
                }
            )
        )
    return pd.concat(partes, ignore_index=True)


def pacote_sintetico(n_estimadores: int = 20) -> dict:
    bruto = leituras_sinteticas(dias=4)
    series = series_por_ponto(bruto)
    validas = pd.concat(linhas_validas_od(s) for s in series.values())
    modelos_od = treinar_od(validas, n_estimadores)
    for serie in series.values():
        serie["od_estimado"] = modelos_od["od"].predict(serie[FEATURES_OD])
    dataset = montar_dataset_risco(series, grupos_dos_pontos(bruto), TILAPIA, cobertura_min_blocos=3)
    modelos_risco = treinar_risco(dataset, n_estimadores)
    return montar_pacote(modelos_od, modelos_risco, TILAPIA, {"sintetico/2023-12.rdb": "0" * 64})
