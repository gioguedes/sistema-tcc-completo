import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import Settings
from src.dados.carregar import carregar_todos
from src.dados.limpar import limpar
from src.faixas import TILAPIA, nivel_geral
from src.pacote import montar_pacote, salvar_pacote
from src.treino.modelo_od import FEATURES_OD, comparar_od, od_fora_da_dobra, treinar_od, treinar_od_central
from src.treino.modelo_risco import avaliar_risco, montar_dataset_risco, treinar_risco
from src.treino.preparar import grupos_dos_pontos, linhas_validas_od, series_por_ponto
from src.treino.relatorio import gerar_relatorio
from src.treino.split import escolher_grupos_teste, linhas_por_grupo, split_temporal, validacao_cruzada

logger = logging.getLogger(__name__)


def treinar(
    bruto: pd.DataFrame, hashes: dict[str, str], caminho_modelos: Path, pasta_relatorios: Path,
    cobertura_min_blocos: int = 3, n_estimadores: int = 300,
) -> Path:
    """Limpa, separa, treina, avalia, grava o pacote de modelos e devolve o caminho do relatório."""
    limpo, removidas = limpar(bruto)
    series = series_por_ponto(limpo)
    grupo_de = grupos_dos_pontos(limpo)
    logger.info("%d linhas brutas, %d após limpeza, %d pontos", len(bruto), len(limpo), len(series))

    validas = pd.concat(
        linhas_validas_od(s).assign(ponto=p, grupo=grupo_de[p]) for p, s in series.items()
    )
    blocos_por_grupo = linhas_por_grupo(validas.groupby("ponto").size().to_dict(), grupo_de)
    grupos_teste = escolher_grupos_teste(blocos_por_grupo)
    grupos_treino = sorted(set(blocos_por_grupo) - set(grupos_teste))
    logger.info("teste: %s | treino: %s", grupos_teste, grupos_treino)

    treino_od, teste_od = validas[validas["grupo"].isin(grupos_treino)], validas[validas["grupo"].isin(grupos_teste)]
    modelos_od = treinar_od(treino_od, n_estimadores)
    od = {
        "teste": comparar_od(treino_od, teste_od, TILAPIA, n_estimadores),
        "validacao_cruzada": validacao_cruzada(treino_od, lambda a, b: comparar_od(a, b, TILAPIA, n_estimadores)),
        "temporal": comparar_od(*split_temporal(treino_od), TILAPIA, n_estimadores),
    }
    logger.info("OD: MAE teste %.3f", od["teste"]["xgboost"]["mae"])

    # OD estimado por bloco: fora da dobra nos corpos de treino, modelo final nos de teste
    oof = treino_od.assign(od_estimado=od_fora_da_dobra(treino_od, n_estimadores))
    for ponto, serie in series.items():
        serie["od_estimado"] = np.nan
        if grupo_de[ponto] in grupos_teste:
            linhas = linhas_validas_od(serie).index
            serie.loc[linhas, "od_estimado"] = modelos_od["od"].predict(serie.loc[linhas, FEATURES_OD])
        else:
            do_ponto = oof[oof["ponto"] == ponto]
            serie.loc[do_ponto.index, "od_estimado"] = do_ponto["od_estimado"].to_numpy()

    dataset = montar_dataset_risco(series, grupo_de, TILAPIA, cobertura_min_blocos)
    treino_risco, teste_risco = dataset[dataset["grupo"].isin(grupos_treino)], dataset[dataset["grupo"].isin(grupos_teste)]
    modelos_risco = treinar_risco(treino_risco, n_estimadores)

    # a regra aplica o estimador de OD aos valores previstos: em cada avaliação ele não pode ter
    # visto os corpos d'água (ou o período) avaliados
    def od_sem(fora: pd.DataFrame):
        return treinar_od_central(treino_od[~treino_od["grupo"].isin(set(fora["grupo"]))], n_estimadores)

    risco_treino_temporal, risco_teste_temporal = split_temporal(treino_risco)
    risco = {
        "teste": avaliar_risco(treino_risco, teste_risco, modelos_od["od"], TILAPIA, n_estimadores),
        "validacao_cruzada": validacao_cruzada(
            treino_risco, lambda a, b: avaliar_risco(a, b, od_sem(b), TILAPIA, n_estimadores)
        ),
        "temporal": avaliar_risco(
            risco_treino_temporal, risco_teste_temporal,
            treinar_od_central(split_temporal(treino_od)[0], n_estimadores), TILAPIA, n_estimadores,
        ),
    }
    logger.info("risco: acurácia teste 1h %.3f", risco["teste"][1]["xgboost"]["acuracia"])

    dominio_od = {g: [float(v) for v in np.percentile(treino_od[g], [1, 99])] for g in FEATURES_OD}
    salvar_pacote(montar_pacote(modelos_od, modelos_risco, TILAPIA, hashes, dominio_od), caminho_modelos)
    niveis = nivel_geral(validas["ph"], validas["temperatura"], validas["od"], TILAPIA).astype(int)
    return gerar_relatorio(
        {
            "criado_em": datetime.now(timezone.utc).isoformat(),
            "pontos": grupo_de,
            "linhas_por_grupo": blocos_por_grupo,
            "grupos_treino": grupos_treino,
            "grupos_teste": grupos_teste,
            "fracao_teste": sum(blocos_por_grupo[g] for g in grupos_teste) / sum(blocos_por_grupo.values()),
            "distribuicao_niveis": np.bincount(niveis, minlength=3).tolist(),
            "linhas_brutas": len(bruto),
            "linhas_limpas": len(limpo),
            "limpeza": removidas,
            "od": od,
            "risco": risco,
            "dominio_od": dominio_od,
            "hashes_datasets": hashes,
        },
        pasta_relatorios,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    bruto, hashes = carregar_todos(settings.ml_datasets_dir / "usgs")
    caminho = treinar(
        bruto, hashes, settings.caminho_modelos, settings.ml_relatorios_dir, settings.ml_cobertura_min_blocos
    )
    logger.info("modelos em %s | relatório em %s", settings.caminho_modelos, caminho)


if __name__ == "__main__":
    main()
