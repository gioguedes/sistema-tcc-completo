import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from src.api.app import criar_app
from src.api.config import ConfigApi
from src.api.dependencias import obter_sessao
from src.api.usuarios import definir_usuario
from src.db.models import Tanque
from src.db.seed import semear
from tests.api.fabricas import SENHA, PublicadorFalso


@pytest.fixture()
def config() -> ConfigApi:
    return ConfigApi(_env_file=None, api_jwt_segredo="s" * 48, api_cookie_seguro=False)


@pytest.fixture()
def publicador() -> PublicadorFalso:
    return PublicadorFalso()


@pytest.fixture()
def cliente(db_session, config, publicador):
    app = criar_app(config, fabrica_sessao=sessionmaker(), publicador=publicador)
    app.dependency_overrides[obter_sessao] = lambda: db_session
    with TestClient(app, base_url="http://testserver/api/v1") as cliente:
        yield cliente


@pytest.fixture()
def usuario(db_session):
    usuario, _ = definir_usuario(db_session, "admin@teste.local", SENHA, nome="Admin Teste", perfil="admin")
    db_session.commit()
    return usuario


@pytest.fixture()
def autenticado(cliente, usuario):
    resposta = cliente.post("/auth/login", json={"email": usuario.email, "senha": SENHA})
    cliente.headers["Authorization"] = f"Bearer {resposta.json()['access_token']}"
    return cliente


@pytest.fixture()
def tanque(db_session) -> Tanque:
    semear(db_session)
    db_session.commit()
    return db_session.scalar(select(Tanque).where(Tanque.nome == "Tanque bancada TCC"))
