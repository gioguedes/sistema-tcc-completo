from pathlib import Path

from src.config import Settings


def _env_minimo(monkeypatch) -> None:
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "piscicultura")
    monkeypatch.setenv("DB_USER", "piscicultura")
    monkeypatch.setenv("DB_PASSWORD", "piscicultura_dev")
    monkeypatch.setenv("ML_DATASETS_DIR", "C:/dados")


def test_settings_le_env_e_monta_url_do_banco(monkeypatch):
    _env_minimo(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql+psycopg://piscicultura:piscicultura_dev@localhost:5432/piscicultura"
    assert settings.ml_datasets_dir == Path("C:/dados")


def test_padroes_do_servico_batem_com_a_spec(monkeypatch):
    _env_minimo(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.ml_intervalo_s == 300
    assert settings.ml_confianca_min == 0.5
    assert settings.ml_cobertura_min_blocos == 3
    assert settings.caminho_modelos == Path("modelos") / "modelos.joblib"
