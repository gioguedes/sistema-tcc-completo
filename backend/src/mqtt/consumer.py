import json
import logging

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session, sessionmaker

from src.mqtt.processor import LeituraProcessor
from src.mqtt.schemas import LeituraMqttPayload

logger = logging.getLogger(__name__)


class ConsumerMqtt:
    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        topico_prefixo: str,
        session_factory: sessionmaker[Session],
        processor: LeituraProcessor,
    ) -> None:
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._topico = f"{topico_prefixo}/+/leituras"
        self._session_factory = session_factory
        self._processor = processor

        # sessão persistente: com client_id fixo e clean_session=False, o broker guarda as leituras
        # QoS 1 que chegarem enquanto a ingestão estiver fora e entrega quando ela voltar
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=f"ingestao-{topico_prefixo}", clean_session=False
        )
        self._client.on_connect = self._ao_conectar
        self._client.on_message = self._ao_receber_mensagem

    def _ao_conectar(self, client, userdata, flags, reason_code, properties) -> None:
        logger.info("conectado ao broker %s:%s, assinando %s", self._broker_host, self._broker_port, self._topico)
        client.subscribe(self._topico, qos=1)

    def _ao_receber_mensagem(self, client, userdata, msg) -> None:
        try:
            dados = json.loads(msg.payload)
            payload = LeituraMqttPayload(**dados)
        except Exception:
            logger.exception("payload invalido no topico %s, descartando", msg.topic)
            return

        # o broker é público: o nó só publica no tópico do próprio MAC, então MAC do tópico
        # diferente do MAC do payload é leitura forjada ou nó mal configurado
        mac_topico = msg.topic.split("/")[-2] if msg.topic.count("/") >= 2 else ""
        if mac_topico.lower() != payload.mac.replace(":", "").lower():
            logger.warning("mac do payload (%s) nao bate com o do topico %s, descartando", payload.mac, msg.topic)
            return

        try:
            with self._session_factory() as session:
                self._processor.processar_payload(session, payload)
        except Exception:
            logger.exception("falha ao gravar leitura do topico %s, descartando", msg.topic)

    def rodar_para_sempre(self) -> None:
        self._client.connect(self._broker_host, self._broker_port)
        self._client.loop_forever()