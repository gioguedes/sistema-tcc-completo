"""Alertas e eventos (UC04, UC07).

Quem grava em `alertas` e o servico de alertas do ML (src.servico.alertas), ao avisar o webhook do N8N;
a API so le. Os eventos juntam os alertas e os acionamentos do aerador, do mais recente para o mais antigo.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, literal, select, union_all

from src.api.dependencias import Sessao, usuario_atual
from src.api.esquemas import (
    AlertaSaida,
    EventoAcionamento,
    EventoAlerta,
    PaginaAlertas,
    PaginaEventos,
    StatusAlerta,
)
from src.api.estado import carregar_situacoes
from src.db.models import AcionamentoAtuador, Alerta, Especie, Tanque

router = APIRouter(tags=["alertas"], dependencies=[Depends(usuario_atual)])

NumeroPagina = Annotated[int, Query(ge=1)]
PorPagina = Annotated[int, Query(ge=1, le=50)]


def _em_utc(momento: datetime) -> datetime:
    # data sem fuso e lida como UTC, como em /tanques/{id}/leituras
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def _ids_dos_ativos(sessao) -> list[int]:
    """Ultimo alerta de cada tanque, se ele e critico e o nivel atual do tanque nao o desmente.

    O servico de alertas grava um alerta "normal" quando a condicao encerra. Conferir o nivel atual
    evita mostrar um alerta antigo como ativo quando o servico esta parado ou sem webhook.
    """
    ordem = func.row_number().over(
        partition_by=Alerta.id_tanque, order_by=(Alerta.criado_em.desc(), Alerta.id.desc())
    )
    ultimos = select(Alerta.id, Alerta.id_tanque, Alerta.nivel_risco, ordem.label("ordem")).subquery()
    criticos = {
        id_tanque: id_alerta
        for id_tanque, id_alerta in sessao.execute(
            select(ultimos.c.id_tanque, ultimos.c.id).where(ultimos.c.ordem == 1, ultimos.c.nivel_risco == "critico")
        )
    }
    if not criticos:
        return []
    tanques = list(sessao.scalars(select(Tanque).where(Tanque.id.in_(criticos))))
    especies = {e.id: e for e in sessao.scalars(select(Especie))}
    situacoes = carregar_situacoes(sessao, tanques, especies, datetime.now(timezone.utc))
    # sem previsao valida o nivel atual e desconhecido (None): nao ha como desmentir, vale o ultimo alerta
    return [criticos[t.id] for t in tanques if situacoes[t.id].nivel_risco in (None, "critico")]


@router.get("/alertas", response_model=PaginaAlertas)
def listar_alertas(
    sessao: Sessao,
    tanque: int | None = None,
    status: StatusAlerta | None = None,
    ativos: bool = False,
    desde: datetime | None = None,
    ate: datetime | None = None,
    pagina: NumeroPagina = 1,
    por_pagina: PorPagina = 10,
) -> PaginaAlertas:
    filtros = []
    if tanque is not None:
        filtros.append(Alerta.id_tanque == tanque)
    if status is not None:
        filtros.append(Alerta.status == status)
    if desde is not None:
        filtros.append(Alerta.criado_em >= _em_utc(desde))
    if ate is not None:
        filtros.append(Alerta.criado_em <= _em_utc(ate))
    if ativos:
        filtros.append(Alerta.id.in_(_ids_dos_ativos(sessao)))

    total = sessao.scalar(select(func.count()).select_from(Alerta).where(*filtros))
    linhas = sessao.execute(
        select(Alerta, Tanque.nome)
        .join(Tanque, Tanque.id == Alerta.id_tanque)
        .where(*filtros)
        .order_by(Alerta.criado_em.desc(), Alerta.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()
    itens = [
        AlertaSaida(
            id=a.id,
            id_tanque=a.id_tanque,
            tanque_nome=nome,
            id_previsao=a.id_previsao,
            mensagem=a.mensagem,
            recomendacoes=[a.recomendacao] if a.recomendacao else [],
            nivel_risco=a.nivel_risco,
            parametro=a.parametro,
            canal=a.canal,
            status=a.status,
            ts_envio=a.ts_envio,
            criado_em=a.criado_em,
        )
        for a, nome in linhas
    ]
    return PaginaAlertas(itens=itens, total=total, pagina=pagina, por_pagina=por_pagina)


@router.get("/eventos", response_model=PaginaEventos)
def listar_eventos(sessao: Sessao, pagina: NumeroPagina = 1, por_pagina: PorPagina = 10) -> PaginaEventos:
    # a pagina e cortada no banco, sobre as duas tabelas juntas; so depois vem o conteudo de cada linha
    linha_do_tempo = union_all(
        select(literal("alerta").label("tipo"), Alerta.id.label("id"), Alerta.criado_em.label("ts")),
        select(literal("acionamento"), AcionamentoAtuador.id, AcionamentoAtuador.ts_acionamento),
    ).subquery()
    total = sessao.scalar(select(func.count()).select_from(linha_do_tempo))
    da_pagina = sessao.execute(
        select(linha_do_tempo.c.tipo, linha_do_tempo.c.id)
        .order_by(linha_do_tempo.c.ts.desc(), linha_do_tempo.c.tipo, linha_do_tempo.c.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()

    ids_alertas = [id_ for tipo, id_ in da_pagina if tipo == "alerta"]
    ids_acionamentos = [id_ for tipo, id_ in da_pagina if tipo == "acionamento"]
    alertas = {
        a.id: EventoAlerta(
            id=f"alerta-{a.id}",
            id_tanque=a.id_tanque,
            tanque_nome=nome,
            ocorrido_em=a.criado_em,
            nivel_risco=a.nivel_risco,
            mensagem=a.mensagem,
        )
        for a, nome in sessao.execute(
            select(Alerta, Tanque.nome).join(Tanque, Tanque.id == Alerta.id_tanque).where(Alerta.id.in_(ids_alertas))
        )
    }
    acionamentos = {
        a.id: EventoAcionamento(
            id=f"acionamento-{a.id}",
            id_tanque=a.id_tanque,
            tanque_nome=nome,
            ocorrido_em=a.ts_acionamento,
            acao=a.acao,
            # disparado por uma previsao = automatico; comando do painel = manual
            automatico=a.id_previsao is not None,
            motivo=a.motivo,
        )
        for a, nome in sessao.execute(
            select(AcionamentoAtuador, Tanque.nome)
            .join(Tanque, Tanque.id == AcionamentoAtuador.id_tanque)
            .where(AcionamentoAtuador.id.in_(ids_acionamentos))
        )
    }
    itens = [alertas[id_] if tipo == "alerta" else acionamentos[id_] for tipo, id_ in da_pagina]
    return PaginaEventos(itens=itens, total=total, pagina=pagina, por_pagina=por_pagina)
