from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from src.api.comando_aerador import PublicadorMqtt
from src.api.config import ConfigApi
from src.api.rotas import aerador, alertas, autenticacao, cadastro, catalogos, tanques
from src.config import Settings
from src.db.session import criar_engine, criar_session_factory

PREFIXO = "/api/v1"


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    app.state.publicador.iniciar()
    yield
    app.state.publicador.parar()


def criar_app(
    config: ConfigApi | None = None,
    fabrica_sessao: sessionmaker[Session] | None = None,
    publicador: PublicadorMqtt | None = None,
) -> FastAPI:
    config = config or ConfigApi()
    if fabrica_sessao is None or publicador is None:
        settings = Settings()
        fabrica_sessao = fabrica_sessao or criar_session_factory(criar_engine(settings))
        publicador = publicador or PublicadorMqtt(
            settings.mqtt_broker_host, settings.mqtt_broker_port, settings.mqtt_topic_prefix
        )

    app = FastAPI(
        title="API do Painel Aquicola",
        version="0.3.0",
        # documentacao dentro do prefixo para abrir tambem pelo proxy do front (/api/v1/docs)
        docs_url=f"{PREFIXO}/docs",
        openapi_url=f"{PREFIXO}/openapi.json",
        redoc_url=None,
        lifespan=_ciclo_de_vida,
    )
    app.state.config = config
    app.state.fabrica_sessao = fabrica_sessao
    app.state.publicador = publicador
    for modulo in (autenticacao, catalogos, tanques, cadastro, aerador, alertas):
        app.include_router(modulo.router, prefix=PREFIXO)
    return app
