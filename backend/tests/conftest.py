import psycopg
import pytest
from psycopg import errors
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.config import Settings
from src.db.models import Base

NOME_BANCO_TESTE = "piscicultura_test"


def _dsn_admin(settings: Settings) -> str:
    return (
        f"postgresql://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/postgres"
    )


def _database_url_teste(settings: Settings) -> str:
    return (
        f"postgresql+psycopg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{NOME_BANCO_TESTE}"
    )


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def engine(settings: Settings):
    with psycopg.connect(_dsn_admin(settings), autocommit=True) as conn:
        try:
            conn.execute(f'CREATE DATABASE "{NOME_BANCO_TESTE}"')
        except errors.DuplicateDatabase:
            pass

    engine = create_engine(_database_url_teste(settings))
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(engine) -> Session:
    connection = engine.connect()
    transacao = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transacao.rollback()
    connection.close()