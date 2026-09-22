from src.config import Settings


def test_settings_reads_env_and_builds_database_url(monkeypatch):
    monkeypatch.setenv("MQTT_BROKER_HOST", "broker.hivemq.com")
    monkeypatch.setenv("MQTT_BROKER_PORT", "1883")
    monkeypatch.setenv("MQTT_TOPIC_PREFIX", "tcc-piscicultura-morgado")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "piscicultura")
    monkeypatch.setenv("DB_USER", "piscicultura")
    monkeypatch.setenv("DB_PASSWORD", "piscicultura_dev")

    settings = Settings(_env_file=None)

    assert settings.mqtt_broker_host == "broker.hivemq.com"
    assert settings.mqtt_broker_port == 1883
    assert settings.database_url == (
        "postgresql+psycopg://piscicultura:piscicultura_dev"
        "@localhost:5432/piscicultura"
    )