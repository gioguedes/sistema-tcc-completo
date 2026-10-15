"""Comando manual do aerador pelo painel (F-02 do Figma).

Qualquer usuario autenticado pode ligar ou desligar: quem cuida do tanque age na emergencia.
O acionamento e registrado em acionamentos_atuador e publicado no broker (ver comando_aerador.py).
A resposta e 202: o broker recebeu o comando, mas o no ainda nao confirma que o rele mudou.
"""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.dependencias import Publicador, Sessao, UsuarioAtual
from src.api.esquemas import AcionamentoSaida
from src.db.models import AcionamentoAtuador, Dispositivo

router = APIRouter(tags=["aerador"])

TAMANHO_MOTIVO = 160  # VARCHAR(160) em acionamentos_atuador


class ComandoAerador(BaseModel):
    acao: Literal["ligar", "desligar"]


@router.post("/dispositivos/{id_dispositivo}/aerador", status_code=202, response_model=AcionamentoSaida)
def comandar_aerador(
    id_dispositivo: int, dados: ComandoAerador, usuario: UsuarioAtual, sessao: Sessao, publicador: Publicador
) -> AcionamentoAtuador:
    dispositivo = sessao.get(Dispositivo, id_dispositivo)
    if dispositivo is None:
        raise HTTPException(404, "Dispositivo não encontrado.")

    agora = datetime.now(timezone.utc)
    acionamento = AcionamentoAtuador(
        id_dispositivo=dispositivo.id,
        id_tanque=dispositivo.id_tanque,
        id_previsao=None,
        acao=dados.acao,
        motivo=f"Comando manual de {usuario.nome} pelo painel."[:TAMANHO_MOTIVO],
        ts_acionamento=agora,
    )
    sessao.add(acionamento)
    sessao.flush()  # o id do acionamento vai no payload, para o no registrar qual comando cumpriu

    if not publicador.publicar_aerador(dispositivo.mac_address, dados.acao, acionamento.id, int(agora.timestamp())):
        # sem confirmacao do broker o comando nao saiu: nao fica registro de um acionamento que nao houve
        sessao.rollback()
        raise HTTPException(503, "Não foi possível enviar o comando ao nó sensor. Tente novamente em instantes.")
    sessao.commit()
    return acionamento
