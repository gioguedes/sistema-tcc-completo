import argparse
import json
import time

import paho.mqtt.client as mqtt

from src.config import Settings
from src.db.seed import MAC_DISPOSITIVO_PADRAO


def payloads(minutos: int, ph_inicial: float, ph_final: float, temperatura: float, agora: int) -> list[dict]:
    """Uma leitura por minuto terminando em `agora`, com o pH variando em linha reta."""
    mac = MAC_DISPOSITIVO_PADRAO.replace(":", "")
    passo = (ph_final - ph_inicial) / max(minutos - 1, 1)
    return [
        {
            "mac": mac,
            "ts": agora - 60 * (minutos - 1 - i),
            "ph": round(ph_inicial + passo * i, 3),
            "temperatura": temperatura,
            "turbidez": 10.0,
        }
        for i in range(minutos)
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Publica leituras simuladas (ts retroativo) no broker do .env")
    parser.add_argument("--minutos", type=int, default=90)
    parser.add_argument("--ph-inicial", type=float, default=7.0)
    parser.add_argument("--ph-final", type=float, default=4.5)
    parser.add_argument("--temperatura", type=float, default=26.0)
    args = parser.parse_args(argv)

    settings = Settings()
    topico = f"{settings.mqtt_topic_prefix}/{MAC_DISPOSITIVO_PADRAO.replace(':', '')}/leituras"
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cliente.connect(settings.mqtt_broker_host, settings.mqtt_broker_port)
    cliente.loop_start()
    for payload in payloads(args.minutos, args.ph_inicial, args.ph_final, args.temperatura, int(time.time())):
        cliente.publish(topico, json.dumps(payload), qos=1).wait_for_publish(10)
    cliente.loop_stop()
    cliente.disconnect()
    print(f"{args.minutos} leituras publicadas em {topico}")


if __name__ == "__main__":
    main()
