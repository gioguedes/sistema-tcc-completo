from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import Settings


def criar_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url)


def criar_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)