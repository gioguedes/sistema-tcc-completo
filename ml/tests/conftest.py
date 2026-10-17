import os
import subprocess
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine, text

from src.config import Settings
from tests.fabricas import pacote_sintetico

NOME_BANCO_TESTE = "piscicultura_ml_test"
PASTA_BACKEND = Path(__file__).resolve().parents[2] / "backend"
DDL_TC1 = PASTA_BACKEND / "db" / "init" / "01_apendice_a_ddl.sql"
PYTHON_BACKEND = PASTA_BACKEND / ".venv" / "Scripts" / "python.exe"


def _dsn(settings: Settings, banco: str) -> str:
    return f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{banco}"


def _recriar_banco_com_schema_real(settings: Settings) -> None:
    """Banco novo = DDL do TC1 + migrações do backend: o mesmo caminho do banco de verdade."""
    with psycopg.connect(_dsn(settings, "postgres"), autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{NOME_BANCO_TESTE}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{NOME_BANCO_TESTE}"')

    # um comando por vez: o continuous aggregate do DDL não roda dentro de transação
    comandos = [c.strip() for c in DDL_TC1.read_text(encoding="utf-8").split(";")]
    with psycopg.connect(_dsn(settings, NOME_BANCO_TESTE), autocommit=True) as conn:
        for comando in comandos:
            sem_comentarios = "\n".join(l for l in comando.splitlines() if not l.strip().startswith("--"))
            if sem_comentarios.strip():
                conn.execute(sem_comentarios)

    subprocess.run(
        [str(PYTHON_BACKEND), "-m", "alembic", "upgrade", "head"],
        cwd=PASTA_BACKEND,
        env={**os.environ, "DB_NAME": NOME_BANCO_TESTE},
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session")
def engine():
    settings = Settings()
    _recriar_banco_com_schema_real(settings)
    url = settings.database_url.rsplit("/", 1)[0] + f"/{NOME_BANCO_TESTE}"
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine):
    yield engine
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE previsoes, leituras, sensores, tipos_sensor, dispositivos, "
                "tanques, especies, usuarios RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture(scope="session")
def pacote():
    return pacote_sintetico()
