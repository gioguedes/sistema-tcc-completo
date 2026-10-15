from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.api.comando_aerador import PublicadorMqtt
from src.api.config import ConfigApi
from src.api.seguranca import ACESSO, ler_token
from src.db.models import Usuario


def obter_sessao(request: Request) -> Iterator[Session]:
    with request.app.state.fabrica_sessao() as sessao:
        yield sessao


def obter_config(request: Request) -> ConfigApi:
    return request.app.state.config


def obter_publicador(request: Request) -> PublicadorMqtt:
    return request.app.state.publicador


Sessao = Annotated[Session, Depends(obter_sessao)]
Config = Annotated[ConfigApi, Depends(obter_config)]
Publicador = Annotated[PublicadorMqtt, Depends(obter_publicador)]

_bearer = HTTPBearer(auto_error=False)


def usuario_atual(
    sessao: Sessao,
    config: Config,
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Usuario:
    dados = ler_token(credenciais.credentials, ACESSO, config.api_jwt_segredo) if credenciais else None
    usuario = sessao.get(Usuario, int(dados["sub"])) if dados else None
    if usuario is None:
        # o front renova a sessao uma vez pelo cookie e, se falhar, volta ao login
        raise HTTPException(401, "Sessão expirada. Entre novamente.", headers={"WWW-Authenticate": "Bearer"})
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(usuario_atual)]


def administrador(usuario: UsuarioAtual) -> Usuario:
    # cadastros so para o perfil admin (UC01; decisao I-04 da auditoria do front)
    if usuario.perfil != "admin":
        raise HTTPException(403, "Acesso restrito a administradores.")
    return usuario


Administrador = Annotated[Usuario, Depends(administrador)]
