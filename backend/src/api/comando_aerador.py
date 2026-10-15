"""Comando do aerador: a API publica no mesmo broker da ingestao e o no sensor assina.

Protocolo (o firmware precisa seguir o mesmo):
- topico `<MQTT_TOPIC_PREFIX>/<mac sem separador, minusculo>/aerador`, irmao do `.../leituras`;
- payload `{"acao": "ligar" | "desligar", "id": <id em acionamentos_atuador>, "ts": <epoch UTC>}`;
- QoS 1 e **retido**: o broker guarda o ultimo comando, e o no que reinicia ou volta de uma
  queda de rede recebe o estado pedido assim que assina o topico.
"""

import json
import logging
import uuid

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

# tempo para o broker confirmar o QoS 1 (PUBACK) antes de a API desistir
TEMPO_LIMITE_S = 5.0


def topico_aerador(prefixo: str, mac: str) -> str:
    # mesmo formato do mac no topico de leituras (macLimpo() no firmware)
    return f"{prefixo}/{mac.replace(':', '').lower()}/aerador"


class PublicadorMqtt:
    def __init__(self, broker_host: str, broker_port: int, topico_prefixo: str) -> None:
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._prefixo = topico_prefixo
        # id proprio por processo, para nao derrubar a conexao da ingestao nem de outra API
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"api-painel-{uuid.uuid4().hex[:8]}")

    def iniciar(self) -> None:
        # conecta em segundo plano; o paho reconecta sozinho se o broker cair
        self._client.connect_async(self._broker_host, self._broker_port)
        self._client.loop_start()
        logger.info("publicador de comandos ligado ao broker %s:%s", self._broker_host, self._broker_port)

    def parar(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()

    def publicar_aerador(self, mac: str, acao: str, id_acionamento: int, ts: int) -> bool:
        """True quando o broker confirmou o recebimento (PUBACK); nao confirma que o no executou."""
        if not self._client.is_connected():
            logger.warning("comando do aerador nao enviado: sem conexao com o broker")
            return False
        topico = topico_aerador(self._prefixo, mac)
        mensagem = self._client.publish(
            topico, json.dumps({"acao": acao, "id": id_acionamento, "ts": ts}), qos=1, retain=True
        )
        try:
            mensagem.wait_for_publish(TEMPO_LIMITE_S)
        except (RuntimeError, ValueError):
            logger.exception("falha ao publicar em %s", topico)
            return False
        return mensagem.is_published()
