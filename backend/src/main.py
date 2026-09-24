import logging

from src.config import Settings
from src.db.session import criar_engine, criar_session_factory
from src.mqtt.consumer import ConsumerMqtt
from src.mqtt.processor import LeituraProcessor


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    settings = Settings()
    engine = criar_engine(settings)
    session_factory = criar_session_factory(engine)
    processor = LeituraProcessor()

    consumer = ConsumerMqtt(
        broker_host=settings.mqtt_broker_host,
        broker_port=settings.mqtt_broker_port,
        topico_prefixo=settings.mqtt_topic_prefix,
        session_factory=session_factory,
        processor=processor,
    )

    logger.info("iniciando consumo do broker %s:%s", settings.mqtt_broker_host, settings.mqtt_broker_port)
    consumer.rodar_para_sempre()


if __name__ == "__main__":
    main()