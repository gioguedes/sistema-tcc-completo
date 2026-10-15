"""Alertas e eventos (UC04, UC07).

O sub-projeto 4 (N8N/WhatsApp) ainda nao grava alertas, entao a lista de alertas vem vazia:
o painel mostra o estado vazio, sem erro. Os filtros do contrato sao aceitos e ignorados.
Os eventos ja trazem os acionamentos do aerador; os alertas entram quando existirem.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from src.api.dependencias import Sessao, usuario_atual
from src.api.esquemas import EventoAcionamento, Pagina, PaginaEventos
from src.db.models import AcionamentoAtuador, Tanque

router = APIRouter(tags=["alertas"], dependencies=[Depends(usuario_atual)])

NumeroPagina = Annotated[int, Query(ge=1)]
PorPagina = Annotated[int, Query(ge=1, le=50)]


@router.get("/alertas", response_model=Pagina)
def listar_alertas(pagina: NumeroPagina = 1, por_pagina: PorPagina = 10) -> Pagina:
    return Pagina(itens=[], total=0, pagina=pagina, por_pagina=por_pagina)


@router.get("/eventos", response_model=PaginaEventos)
def listar_eventos(sessao: Sessao, pagina: NumeroPagina = 1, por_pagina: PorPagina = 10) -> PaginaEventos:
    total = sessao.scalar(select(func.count()).select_from(AcionamentoAtuador))
    linhas = sessao.execute(
        select(AcionamentoAtuador, Tanque.nome)
        .join(Tanque, Tanque.id == AcionamentoAtuador.id_tanque)
        .order_by(AcionamentoAtuador.ts_acionamento.desc(), AcionamentoAtuador.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()
    itens = [
        EventoAcionamento(
            id=f"acionamento-{a.id}",
            id_tanque=a.id_tanque,
            tanque_nome=nome,
            ocorrido_em=a.ts_acionamento,
            acao=a.acao,
            # disparado por uma previsao = automatico; comando do painel = manual
            automatico=a.id_previsao is not None,
            motivo=a.motivo,
        )
        for a, nome in linhas
    ]
    return PaginaEventos(itens=itens, total=total, pagina=pagina, por_pagina=por_pagina)
