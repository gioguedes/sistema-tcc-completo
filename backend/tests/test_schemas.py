import pytest
from pydantic import ValidationError

from src.mqtt.schemas import LeituraMqttPayload


def test_payload_valido_com_ts_epoch_e_mac_sem_separador():
    payload = LeituraMqttPayload(
        mac="a4f00f643c70",
        ts=1758499200,
        ph=6.8,
        temperatura=27.9,
        turbidez=11.7,
    )

    assert payload.mac_com_separador == "a4:f0:0f:64:3c:70"
    assert payload.ts_utc.tzinfo is not None
    assert payload.valores_por_grandeza() == {"ph": 6.8, "temperatura": 27.9, "turbidez": 11.7}


def test_payload_com_grandeza_nula_e_descartada_do_wide_narrow():
    payload = LeituraMqttPayload(
        mac="a4f00f643c70", ts=1758499200, ph=None, temperatura=27.9, turbidez=11.7
    )

    assert payload.valores_por_grandeza() == {"temperatura": 27.9, "turbidez": 11.7}


def test_payload_sem_mac_falha_validacao():
    with pytest.raises(ValidationError):
        LeituraMqttPayload(ts=1758499200, ph=6.8, temperatura=27.9, turbidez=11.7)