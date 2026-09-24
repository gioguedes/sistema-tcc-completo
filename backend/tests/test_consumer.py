import logging
from unittest.mock import MagicMock

from src.mqtt.consumer import ConsumerMqtt


class _MensagemFake:
    def __init__(self, topic: str, payload: bytes) -> None:
        self.topic = topic
        self.payload = payload


def _consumer(processor, session_factory=None) -> ConsumerMqtt:
    return ConsumerMqtt(
        broker_host="localhost",
        broker_port=1884,
        topico_prefixo="tcc-piscicultura-morgado",
        session_factory=session_factory or MagicMock(),
        processor=processor,
    )


def test_mensagem_valida_e_repassada_ao_processor():
    processor = MagicMock()
    session_factory = MagicMock()
    sessao_fake = MagicMock()
    session_factory.return_value.__enter__.return_value = sessao_fake

    consumer = _consumer(processor, session_factory)
    payload_json = (
        b'{"mac": "a4f00f643c70", "ts": 1758499200, '
        b'"ph": 6.8, "temperatura": 27.9, "turbidez": 11.7}'
    )
    mensagem = _MensagemFake("tcc-piscicultura-morgado/a4f00f643c70/leituras", payload_json)

    consumer._ao_receber_mensagem(None, None, mensagem)

    processor.processar_payload.assert_called_once()
    _, payload_chamado = processor.processar_payload.call_args.args
    assert payload_chamado.mac == "a4f00f643c70"
    assert payload_chamado.ph == 6.8


def test_mensagem_invalida_e_descartada_sem_lancar(caplog):
    processor = MagicMock()
    consumer = _consumer(processor)
    mensagem = _MensagemFake("tcc-piscicultura-morgado/a4f00f643c70/leituras", b"isso nao e json")

    with caplog.at_level(logging.ERROR):
        consumer._ao_receber_mensagem(None, None, mensagem)

    processor.processar_payload.assert_not_called()
    assert "payload invalido" in caplog.text