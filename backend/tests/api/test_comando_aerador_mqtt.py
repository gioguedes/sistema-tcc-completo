"""Publicador de verdade contra o broker de teste (mosquitto-test do docker-compose, porta 1884)."""

import json
import time
import uuid

import paho.mqtt.client as mqtt

from src.api.comando_aerador import PublicadorMqtt, topico_aerador

BROKER = ("localhost", 1884)


def _esperar(condicao, segundos: float = 5.0) -> bool:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicao():
            return True
        time.sleep(0.05)
    return False


def test_topico_usa_o_mac_sem_separador_como_o_firmware():
    assert topico_aerador("tcc-piscicultura-morgado", "A4:F0:0F:64:3C:70") == (
        "tcc-piscicultura-morgado/a4f00f643c70/aerador"
    )


def test_comando_fica_retido_para_o_no_que_conectar_depois():
    prefixo = f"teste-api-{uuid.uuid4().hex[:6]}"
    publicador = PublicadorMqtt(*BROKER, prefixo)
    publicador.iniciar()
    try:
        assert _esperar(publicador._client.is_connected)
        assert publicador.publicar_aerador("a4:f0:0f:64:3c:70", "ligar", 42, 1791590400)
    finally:
        publicador.parar()

    # o "no" so assina depois da publicacao: recebe o comando porque ele ficou retido
    recebidas: list[mqtt.MQTTMessage] = []
    no = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    no.on_message = lambda client, userdata, msg: recebidas.append(msg)
    no.connect(*BROKER)
    topico = f"{prefixo}/a4f00f643c70/aerador"
    no.subscribe(topico, qos=1)
    no.loop_start()
    try:
        assert _esperar(lambda: recebidas)
        assert recebidas[0].retain
        assert json.loads(recebidas[0].payload) == {"acao": "ligar", "id": 42, "ts": 1791590400}
    finally:
        no.publish(topico, b"", qos=1, retain=True).wait_for_publish(5)  # apaga o retido do teste
        no.loop_stop()
        no.disconnect()


def test_sem_conexao_com_o_broker_nao_publica():
    publicador = PublicadorMqtt("localhost", 1, "teste")  # nunca iniciado
    assert publicador.publicar_aerador("a4:f0:0f:64:3c:70", "ligar", 1, 0) is False
