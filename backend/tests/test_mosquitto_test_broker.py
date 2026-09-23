import json
import time

import paho.mqtt.client as mqtt


def test_mosquitto_test_aceita_publish_e_subscribe():
    recebidas: list[bytes] = []

    def on_message(client, userdata, msg):
        recebidas.append(msg.payload)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect("localhost", 1884)
    client.subscribe("teste/fumaca")
    client.loop_start()

    client.publish("teste/fumaca", json.dumps({"ok": True}))
    time.sleep(0.5)

    client.loop_stop()
    client.disconnect()

    assert len(recebidas) == 1
    assert json.loads(recebidas[0]) == {"ok": True}