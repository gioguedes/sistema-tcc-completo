import argparse
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, create_engine

from src.config import Settings
from src.pacote import carregar_pacote
from src.servico.aerador import ControleAerador, LimitesAerador, PublicadorMqtt
from src.servico.gravar import gravar_previsoes
from src.servico.inferencia import Inferencia
from src.servico.janela import ler_janela, tanques_ativos

logger = logging.getLogger(__name__)


def executar_ciclo(
    engine: Engine,
    inferencia: Inferencia,
    confianca_min: float,
    agora: datetime | None = None,
    aerador: ControleAerador | None = None,
) -> dict[str, int]:
    agora = agora or datetime.now(timezone.utc)
    contagem = {"gravados": 0, "indeterminados": 0, "erros": 0, "aerador": 0}

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
            if aerador is not None:
                contagem["aerador"] += aerador.aplicar(engine, id_tanque, previsoes, agora)
        except Exception:
            # um tanque com problema não pode impedir a previsão dos outros
            logger.exception("tanque %d: erro no ciclo de previsao", id_tanque)
            contagem["erros"] += 1
    return contagem


def _controle_aerador(settings: Settings) -> ControleAerador | None:
    if not settings.ml_aerador_automatico:
        return None
    if not settings.mqtt_broker_host or not settings.mqtt_topic_prefix:
        raise ValueError("ML_AERADOR_AUTOMATICO=true exige MQTT_BROKER_HOST e MQTT_TOPIC_PREFIX")
    if settings.ml_aerador_desliga_od <= settings.ml_aerador_liga_od:
        raise ValueError("ML_AERADOR_DESLIGA_OD precisa ser maior que ML_AERADOR_LIGA_OD (histerese)")
    limites = LimitesAerador(
        liga_od=settings.ml_aerador_liga_od,
        desliga_od=settings.ml_aerador_desliga_od,
        pausa_manual=timedelta(minutes=settings.ml_aerador_pausa_manual_min),
        confianca_min=settings.ml_confianca_min,
    )
    logger.info(
        "aerador automatico ligado: liga < %.1f mg/L, desliga >= %.1f mg/L", limites.liga_od, limites.desliga_od
    )
    publicador = PublicadorMqtt(settings.mqtt_broker_host, settings.mqtt_broker_port, settings.mqtt_topic_prefix)
    return ControleAerador(limites, publicador)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serviço periódico de estimativa de OD e previsão de risco")
    parser.add_argument("--uma-vez", action="store_true", help="roda um ciclo só e sai")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    inferencia = Inferencia(
        carregar_pacote(settings.caminho_modelos), settings.ml_cobertura_min_blocos, settings.ml_altitude_m
    )
    engine = create_engine(settings.database_url)
    aerador = _controle_aerador(settings)
    logger.info("servico de ML iniciado, ciclo a cada %d s", settings.ml_intervalo_s)

    while True:
        try:
            logger.info("ciclo: %s", executar_ciclo(engine, inferencia, settings.ml_confianca_min, aerador=aerador))
        except Exception:
            # banco fora do ar, por exemplo: tenta de novo no próximo ciclo
            logger.exception("ciclo falhou")
        if args.uma_vez:
            break
        time.sleep(settings.ml_intervalo_s)


if __name__ == "__main__":
    main()
