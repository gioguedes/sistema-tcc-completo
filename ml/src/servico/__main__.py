import argparse
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import Engine, create_engine

from src.config import Settings
from src.pacote import carregar_pacote
from src.servico.gravar import gravar_previsoes
from src.servico.inferencia import Inferencia
from src.servico.janela import ler_janela, tanques_ativos

logger = logging.getLogger(__name__)


def executar_ciclo(
    engine: Engine, inferencia: Inferencia, confianca_min: float, agora: datetime | None = None
) -> dict[str, int]:
    agora = agora or datetime.now(timezone.utc)
    contagem = {"gravados": 0, "indeterminados": 0, "erros": 0}

    with engine.connect() as conn:
        tanques = tanques_ativos(conn)

    for id_tanque, faixa in tanques:
        try:
            with engine.begin() as conn:
                previsoes = inferencia.prever(ler_janela(conn, id_tanque, agora), faixa, agora)
                if previsoes is None:
                    logger.info("tanque %d: dados insuficientes, previsao indeterminada", id_tanque)
                    contagem["indeterminados"] += 1
                    continue
                gravar_previsoes(conn, id_tanque, previsoes, agora)
            od = previsoes[0]
            if od.confianca < confianca_min:
                logger.warning("tanque %d: OD estimado %.2f com baixa confianca (%.2f)", id_tanque, od.valor_previsto, od.confianca)
            logger.info(
                "tanque %d: OD %.2f | risco 1h/2h/3h = %s", id_tanque, od.valor_previsto,
                "/".join(p.nivel_risco for p in previsoes[1:]),
            )
            contagem["gravados"] += 1
        except Exception:
            # um tanque com problema não pode impedir a previsão dos outros
            logger.exception("tanque %d: erro no ciclo de previsao", id_tanque)
            contagem["erros"] += 1
    return contagem


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serviço periódico de estimativa de OD e previsão de risco")
    parser.add_argument("--uma-vez", action="store_true", help="roda um ciclo só e sai")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    inferencia = Inferencia(carregar_pacote(settings.caminho_modelos), settings.ml_cobertura_min_blocos)
    engine = create_engine(settings.database_url)
    logger.info("servico de ML iniciado, ciclo a cada %d s", settings.ml_intervalo_s)

    while True:
        try:
            logger.info("ciclo: %s", executar_ciclo(engine, inferencia, settings.ml_confianca_min))
        except Exception:
            # banco fora do ar, por exemplo: tenta de novo no próximo ciclo
            logger.exception("ciclo falhou")
        if args.uma_vez:
            break
        time.sleep(settings.ml_intervalo_s)


if __name__ == "__main__":
    main()
