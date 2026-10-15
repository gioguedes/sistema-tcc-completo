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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def caminho_modelos(self) -> Path:
        return self.ml_modelos_dir / "modelos.joblib"
