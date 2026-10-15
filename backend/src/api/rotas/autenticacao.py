"""Login com JWT (RNF05): access token no corpo, refresh token em cookie HttpOnly."""

import re
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import func, select

from src.api.config import ConfigApi
from src.api.dependencias import Config, Sessao, UsuarioAtual
from src.api.esquemas import Token, UsuarioSaida
from src.api.seguranca import ACESSO, HASH_FICTICIO, RENOVACAO, emitir_token, ler_token, verificar_senha
from src.db.models import Usuario

router = APIRouter(prefix="/auth", tags=["autenticacao"])

COOKIE_RENOVACAO = "renovacao"
# o cookie so viaja para as rotas de autenticacao
CAMINHO_COOKIE = "/api/v1/auth"
# formato que o front envia (+55, DDD e numero): e o que o N8N/Evolution API usa no UC04
REGEX_TELEFONE = re.compile(r"^\+55\d{10,11}$")


class DadosLogin(BaseModel):
    email: str
    senha: str
    lembrar: bool = False


class DadosConta(BaseModel):
    nome: str
    telefone: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise PydanticCustomError("nome_vazio", "Informe seu nome.")
        if len(valor) > 120:
            raise PydanticCustomError("nome_longo", "Use no máximo 120 caracteres.")
        return valor

    @field_validator("telefone")
    @classmethod
    def _telefone(cls, valor: str | None) -> str | None:
        if not valor:
            return None
        if not REGEX_TELEFONE.match(valor):
            raise PydanticCustomError("telefone_invalido", "Informe DDD e número, como (11) 98765-4321.")
        return valor


def _token_de_acesso(id_usuario: int, config: ConfigApi) -> Token:
    token, expira_em = emitir_token(
        id_usuario, ACESSO, timedelta(minutes=config.api_acesso_minutos), config.api_jwt_segredo
    )
    return Token(access_token=token, expira_em=expira_em)


def _apagar_cookie(resposta: Response, config: ConfigApi) -> None:
    resposta.delete_cookie(
        COOKIE_RENOVACAO, path=CAMINHO_COOKIE, secure=config.api_cookie_seguro, httponly=True, samesite="strict"
    )


@router.post("/login", response_model=Token)
def entrar(dados: DadosLogin, resposta: Response, sessao: Sessao, config: Config) -> Token:
    usuario = sessao.scalar(select(Usuario).where(func.lower(Usuario.email) == dados.email.strip().lower()))
    senha_confere = verificar_senha(dados.senha, usuario.senha_hash if usuario else HASH_FICTICIO)
    if usuario is None or not senha_confere:
        raise HTTPException(401, "E-mail ou senha incorretos.")

    validade = (
        timedelta(days=config.api_renovacao_dias_lembrar)
        if dados.lembrar
        else timedelta(hours=config.api_renovacao_horas)
    )
    renovacao, _ = emitir_token(usuario.id, RENOVACAO, validade, config.api_jwt_segredo)
    resposta.set_cookie(
        COOKIE_RENOVACAO,
        renovacao,
        # sem "lembrar de mim" o cookie e de sessao: some quando o navegador fecha
        max_age=int(validade.total_seconds()) if dados.lembrar else None,
        path=CAMINHO_COOKIE,
        secure=config.api_cookie_seguro,
        httponly=True,
        samesite="strict",
    )
    return _token_de_acesso(usuario.id, config)


@router.post("/refresh", response_model=Token)
def renovar(
    sessao: Sessao, config: Config, renovacao: Annotated[str | None, Cookie()] = None
) -> Token | JSONResponse:
    dados = ler_token(renovacao, RENOVACAO, config.api_jwt_segredo) if renovacao else None
    usuario = sessao.get(Usuario, int(dados["sub"])) if dados else None
    if usuario is None:
        resposta = JSONResponse({"detail": "Sessão expirada. Entre novamente."}, status_code=401)
        _apagar_cookie(resposta, config)
        return resposta
    return _token_de_acesso(usuario.id, config)


@router.post("/logout", status_code=204)
def sair(config: Config) -> Response:
    # tokens sem estado no servidor: sair e apagar o cookie; o access token expira sozinho
    resposta = Response(status_code=204)
    _apagar_cookie(resposta, config)
    return resposta


@router.get("/eu", response_model=UsuarioSaida)
def eu(usuario: UsuarioAtual) -> Usuario:
    return usuario


@router.patch("/eu", response_model=UsuarioSaida)
def atualizar_conta(dados: DadosConta, usuario: UsuarioAtual, sessao: Sessao) -> Usuario:
    usuario.nome = dados.nome
    usuario.telefone = dados.telefone
    sessao.commit()
    return usuario
