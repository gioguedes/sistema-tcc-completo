"""Configuração dos alertas: a URL do webhook do N8N, que o serviço de alertas lê a cada ciclo.

Só para administradores, inclusive a leitura: quem tem a URL consegue disparar o workflow.
"""

from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError

from src.api.dependencias import Sessao, administrador
from src.db.models import Configuracao

router = APIRouter(tags=["configuracoes"], dependencies=[Depends(administrador)])

CHAVE_WEBHOOK = "alertas_webhook_url"
TAMANHO_MAXIMO = 500
URL_INVALIDA = "Informe uma URL completa, começando com http:// ou https://."


class ConfigAlertasEntrada(BaseModel):
    webhook_url: str | None = None

    @field_validator("webhook_url")
    @classmethod
    def _url(cls, valor: str | None) -> str | None:
        valor = (valor or "").strip()
        if not valor:
            return None
        if len(valor) > TAMANHO_MAXIMO:
            raise PydanticCustomError("url_longa", f"Use no máximo {TAMANHO_MAXIMO} caracteres.")
        try:
            partes = urlsplit(valor)
            valida = partes.scheme in ("http", "https") and bool(partes.hostname) and " " not in valor
        except ValueError:
            valida = False
        if not valida:
            raise PydanticCustomError("url_invalida", URL_INVALIDA)
        return valor


class ConfigAlertasSaida(BaseModel):
    webhook_url: str | None
    atualizado_em: datetime | None


def _saida(configuracao: Configuracao | None) -> ConfigAlertasSaida:
    if configuracao is None:
        return ConfigAlertasSaida(webhook_url=None, atualizado_em=None)
    return ConfigAlertasSaida(webhook_url=configuracao.valor, atualizado_em=configuracao.atualizado_em)


@router.get("/configuracoes/alertas", response_model=ConfigAlertasSaida)
def buscar_config_alertas(sessao: Sessao) -> ConfigAlertasSaida:
    return _saida(sessao.get(Configuracao, CHAVE_WEBHOOK))


@router.put("/configuracoes/alertas", response_model=ConfigAlertasSaida)
def salvar_config_alertas(dados: ConfigAlertasEntrada, sessao: Sessao) -> ConfigAlertasSaida:
    configuracao = sessao.get(Configuracao, CHAVE_WEBHOOK)
    if dados.webhook_url is None:
        if configuracao is not None:
            sessao.delete(configuracao)
            sessao.commit()
        return _saida(None)
    if configuracao is None:
        configuracao = Configuracao(chave=CHAVE_WEBHOOK)
        sessao.add(configuracao)
    configuracao.valor = dados.webhook_url
    configuracao.atualizado_em = datetime.now(timezone.utc)
    sessao.commit()
    return _saida(configuracao)
