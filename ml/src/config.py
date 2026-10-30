from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    ml_datasets_dir: Path
    ml_modelos_dir: Path = Path("modelos")
    ml_relatorios_dir: Path = Path("relatorios")
    ml_intervalo_s: int = 300
    ml_confianca_min: float = 0.5
    ml_cobertura_min_blocos: int = 3
    # altitude do tanque: o OD de saturação cai com a pressão (cerca de 9% a menos a 760 m)
    ml_altitude_m: float = 0.0

    # aerador automático (desligado por padrão: o comando manual do painel continua valendo)
    ml_aerador_automatico: bool = False
    ml_aerador_liga_od: float = 4.0
    ml_aerador_desliga_od: float = 5.0
    ml_aerador_pausa_manual_min: int = 30
    mqtt_broker_host: str = ""
    mqtt_broker_port: int = 1883
    mqtt_topic_prefix: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def caminho_modelos(self) -> Path:
        return self.ml_modelos_dir / "modelos.joblib"
