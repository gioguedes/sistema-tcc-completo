from datetime import timedelta

from sqlalchemy import select

from src.db.models import AcionamentoAtuador, Alerta, Dispositivo, Tanque
from tests.api.fabricas import MINUTO, agora, gravar_ciclo, gravar_leituras

PH_ALTO = "Tanque bancada TCC: risco crítico. pH 9,18, acima do limite de 8,5."
NORMAL = "Tanque bancada TCC: água fora da condição crítica (pH 8,10 e temperatura 26,0 °C)."
RECOMENDACAO = "Confira o sensor e a água. Se confirmar, faça uma troca parcial de água, sem correções bruscas."


def gravar_alerta(
    db_session,
    tanque: Tanque,
    minutos_atras: float,
    nivel: str | None = "critico",
    parametro: str | None = "ph",
    status: str = "enviado",
    mensagem: str = PH_ALTO,
    recomendacao: str | None = RECOMENDACAO,
) -> Alerta:
    criado = agora() - minutos_atras * MINUTO
    alerta = Alerta(
        id_tanque=tanque.id, id_usuario=tanque.id_usuario, mensagem=mensagem, nivel_risco=nivel,
        parametro=parametro, recomendacao=recomendacao, status=status, criado_em=criado,
        ts_envio=criado + timedelta(seconds=1) if status == "enviado" else None,
    )
    db_session.add(alerta)
    db_session.flush()
    return alerta


def gravar_normal(db_session, tanque: Tanque, minutos_atras: float) -> Alerta:
    return gravar_alerta(
        db_session, tanque, minutos_atras, nivel="otimo", parametro=None, mensagem=NORMAL,
        recomendacao="Nenhuma ação necessária. Mantenha o acompanhamento.",
    )


def _outro_tanque(db_session, tanque: Tanque) -> Tanque:
    outro = Tanque(
        id_usuario=tanque.id_usuario, id_especie=tanque.id_especie, nome="Tanque 2", volume_litros=500,
        quantidade_peixes=10, status="ativo", criado_em=agora(),
    )
    db_session.add(outro)
    db_session.flush()
    return outro


def _ids(resposta) -> list[int]:
    assert resposta.status_code == 200
    return [item["id"] for item in resposta.json()["itens"]]


def test_alerta_gravado_chega_ao_painel_como_foi_enviado(autenticado, db_session, tanque):
    alerta = gravar_alerta(db_session, tanque, 5)
    db_session.commit()

    corpo = autenticado.get("/alertas").json()
    assert (corpo["total"], corpo["pagina"], corpo["por_pagina"]) == (1, 1, 10)
    [item] = corpo["itens"]
    assert item == {
        "id": alerta.id,
        "id_tanque": tanque.id,
        "tanque_nome": "Tanque bancada TCC",
        "id_previsao": None,
        "mensagem": PH_ALTO,
        "recomendacoes": [RECOMENDACAO],
        "nivel_risco": "critico",
        "parametro": "ph",
        "canal": "whatsapp",
        "status": "enviado",
        "ts_envio": item["ts_envio"],
        "criado_em": item["criado_em"],
    }
    assert item["criado_em"].endswith("Z") and item["ts_envio"] > item["criado_em"]


def test_alerta_sem_nivel_nem_recomendacao_nao_quebra_a_lista(autenticado, db_session, tanque):
    gravar_alerta(db_session, tanque, 5, nivel=None, parametro=None, recomendacao=None, status="falha")
    db_session.commit()

    [item] = autenticado.get("/alertas").json()["itens"]
    assert (item["nivel_risco"], item["parametro"], item["recomendacoes"]) == (None, None, [])
    assert (item["status"], item["ts_envio"]) == ("falha", None)


def test_lista_do_mais_recente_para_o_mais_antigo_com_paginacao(autenticado, db_session, tanque):
    antigo = gravar_alerta(db_session, tanque, 30)
    meio = gravar_normal(db_session, tanque, 20)
    novo = gravar_alerta(db_session, tanque, 10)
    db_session.commit()

    primeira = autenticado.get("/alertas", params={"por_pagina": 2})
    assert primeira.json()["total"] == 3
    assert _ids(primeira) == [novo.id, meio.id]
    assert _ids(autenticado.get("/alertas", params={"por_pagina": 2, "pagina": 2})) == [antigo.id]


def test_filtros_por_tanque_status_e_periodo(autenticado, db_session, tanque):
    outro = _outro_tanque(db_session, tanque)
    do_outro = gravar_alerta(db_session, outro, 50)
    falhou = gravar_alerta(db_session, tanque, 40, status="falha")
    recente = gravar_alerta(db_session, tanque, 5)
    db_session.commit()

    assert _ids(autenticado.get("/alertas", params={"tanque": outro.id})) == [do_outro.id]
    assert _ids(autenticado.get("/alertas", params={"status": "falha"})) == [falhou.id]
    assert _ids(autenticado.get("/alertas", params={"tanque": tanque.id, "status": "enviado"})) == [recente.id]

    corte = (agora() - 45 * MINUTO).isoformat()
    assert _ids(autenticado.get("/alertas", params={"ate": corte})) == [do_outro.id]
    assert _ids(autenticado.get("/alertas", params={"desde": corte})) == [recente.id, falhou.id]


def test_filtro_invalido_da_422(autenticado):
    assert autenticado.get("/alertas", params={"status": "lido"}).status_code == 422
    assert autenticado.get("/alertas", params={"desde": "ontem"}).status_code == 422
    assert autenticado.get("/alertas", params={"por_pagina": 51}).status_code == 422


def test_ativo_e_o_ultimo_alerta_do_tanque_enquanto_for_critico(autenticado, db_session, tanque):
    gravar_alerta(db_session, tanque, 30)
    gravar_normal(db_session, tanque, 20)
    db_session.commit()
    assert _ids(autenticado.get("/alertas", params={"ativos": "true"})) == []

    aberto = gravar_alerta(db_session, tanque, 10)
    db_session.commit()
    assert _ids(autenticado.get("/alertas", params={"ativos": "true"})) == [aberto.id]
    # o filtro de ativos não mexe no histórico
    assert autenticado.get("/alertas").json()["total"] == 3


def test_alerta_critico_que_falhou_no_envio_continua_ativo(autenticado, db_session, tanque):
    falhou = gravar_alerta(db_session, tanque, 3, status="falha")
    db_session.commit()
    assert _ids(autenticado.get("/alertas", params={"ativos": "true"})) == [falhou.id]


def test_alerta_critico_antigo_nao_fica_ativo_se_o_tanque_esta_fora_do_critico(autenticado, db_session, tanque):
    # serviço de alertas parado: ninguém gravou o "normal", mas as leituras de agora desmentem o alerta
    gravar_alerta(db_session, tanque, 600)
    t = agora()
    gravar_leituras(db_session, tanque, t - MINUTO, ph=8.1, temperatura=26.0)
    gravar_ciclo(db_session, tanque, t - MINUTO, nivel_od="otimo")
    db_session.commit()
    assert _ids(autenticado.get("/alertas", params={"ativos": "true"})) == []


def test_alerta_critico_segue_ativo_com_o_tanque_em_nivel_critico(autenticado, db_session, tanque):
    aberto = gravar_alerta(db_session, tanque, 4)
    t = agora()
    gravar_leituras(db_session, tanque, t - MINUTO, ph=9.18, temperatura=26.0)
    gravar_ciclo(db_session, tanque, t - MINUTO, nivel_od="otimo")
    db_session.commit()
    assert _ids(autenticado.get("/alertas", params={"ativos": "true"})) == [aberto.id]


def test_ativos_olha_cada_tanque_em_separado(autenticado, db_session, tanque):
    outro = _outro_tanque(db_session, tanque)
    gravar_alerta(db_session, tanque, 30)
    gravar_normal(db_session, tanque, 20)
    aberto = gravar_alerta(db_session, outro, 25)
    db_session.commit()

    assert _ids(autenticado.get("/alertas", params={"ativos": "true"})) == [aberto.id]
    assert _ids(autenticado.get("/alertas", params={"ativos": "true", "tanque": tanque.id})) == []


def test_eventos_juntam_alertas_e_acionamentos_na_ordem_do_tempo(autenticado, db_session, tanque):
    id_dispositivo = db_session.scalar(select(Dispositivo.id).where(Dispositivo.id_tanque == tanque.id))
    gravar_alerta(db_session, tanque, 30)
    db_session.add(
        AcionamentoAtuador(
            id_dispositivo=id_dispositivo, id_tanque=tanque.id, acao="ligar", motivo=None,
            ts_acionamento=agora() - 20 * MINUTO,
        )
    )
    normal = gravar_normal(db_session, tanque, 10)
    db_session.commit()

    pagina = autenticado.get("/eventos").json()
    assert pagina["total"] == 3
    assert [e["tipo"] for e in pagina["itens"]] == ["alerta", "acionamento", "alerta"]
    assert pagina["itens"][0] == {
        "tipo": "alerta",
        "id": f"alerta-{normal.id}",
        "id_tanque": tanque.id,
        "tanque_nome": "Tanque bancada TCC",
        "ocorrido_em": pagina["itens"][0]["ocorrido_em"],
        "nivel_risco": "otimo",
        "mensagem": NORMAL,
    }
    assert pagina["itens"][2]["nivel_risco"] == "critico"

    segunda = autenticado.get("/eventos", params={"por_pagina": 2, "pagina": 2}).json()
    assert [e["tipo"] for e in segunda["itens"]] == ["alerta"]
