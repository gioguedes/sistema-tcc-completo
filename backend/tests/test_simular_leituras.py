from scripts.simular_leituras import payloads
from src.mqtt.schemas import LeituraMqttPayload


def test_payloads_terminam_agora_um_por_minuto_com_ph_em_rampa():
    gerados = payloads(minutos=90, ph_inicial=7.0, ph_final=4.5, temperatura=26.0, agora=1_800_000_000)
    assert len(gerados) == 90
    assert gerados[-1]["ts"] == 1_800_000_000
    assert gerados[1]["ts"] - gerados[0]["ts"] == 60
    assert gerados[0]["ph"] == 7.0
    assert gerados[-1]["ph"] == 4.5


def test_payloads_passam_na_validacao_do_consumer():
    for payload in payloads(minutos=3, ph_inicial=7.0, ph_final=6.0, temperatura=26.0, agora=1_800_000_000):
        LeituraMqttPayload(**payload)
