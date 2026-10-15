from datetime import timedelta

from sqlalchemy import func, select

from src.api.usuarios import definir_usuario
from src.db.models import AcionamentoAtuador, Dispositivo, Previsao
from tests.api.fabricas import SENHA, agora, gravar_ciclo


def _id_dispositivo(db_session, tanque) -> int:
    return db_session.scalar(select(Dispositivo.id).where(Dispositivo.id_tanque == tanque.id))


def _total_acionamentos(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(AcionamentoAtuador))


def test_ligar_registra_o_acionamento_e_publica_o_comando(autenticado, db_session, tanque, publicador):
    id_dispositivo = _id_dispositivo(db_session, tanque)
    resposta = autenticado.post(f"/dispositivos/{id_dispositivo}/aerador", json={"acao": "ligar"})

    assert resposta.status_code == 202, resposta.text
    corpo = resposta.json()
    assert corpo["acao"] == "ligar"
    assert corpo["motivo"] == "Comando manual de Admin Teste pelo painel."
    assert corpo["ts_acionamento"].endswith("Z")

    [comando] = publicador.publicados
    assert comando == {"mac": "a4:f0:0f:64:3c:70", "acao": "ligar", "id": corpo["id"], "ts": comando["ts"]}
    acionamento = db_session.get(AcionamentoAtuador, corpo["id"])
    assert (acionamento.id_dispositivo, acionamento.id_tanque, acionamento.id_previsao) == (
        id_dispositivo, tanque.id, None,
    )


def test_produtor_tambem_comanda_o_aerador(cliente, db_session, tanque, publicador):
    definir_usuario(db_session, "produtor@teste.local", SENHA, nome="Produtor", perfil="operador")
    db_session.commit()
    token = cliente.post("/auth/login", json={"email": "produtor@teste.local", "senha": SENHA}).json()["access_token"]

    resposta = cliente.post(
        f"/dispositivos/{_id_dispositivo(db_session, tanque)}/aerador",
        json={"acao": "desligar"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 202
    assert publicador.publicados[0]["acao"] == "desligar"


def test_broker_fora_do_ar_da_503_e_nao_registra(autenticado, db_session, tanque, publicador):
    publicador.disponivel = False
    resposta = autenticado.post(f"/dispositivos/{_id_dispositivo(db_session, tanque)}/aerador", json={"acao": "ligar"})

    assert resposta.status_code == 503
    assert resposta.json()["detail"] == "Não foi possível enviar o comando ao nó sensor. Tente novamente em instantes."
    assert _total_acionamentos(db_session) == 0


def test_validacoes(cliente, autenticado, db_session, tanque, publicador):
    id_dispositivo = _id_dispositivo(db_session, tanque)
    assert autenticado.post("/dispositivos/999999/aerador", json={"acao": "ligar"}).status_code == 404
    assert autenticado.post(f"/dispositivos/{id_dispositivo}/aerador", json={"acao": "girar"}).status_code == 422
    sem_token = cliente.post(
        f"/dispositivos/{id_dispositivo}/aerador", json={"acao": "ligar"}, headers={"Authorization": ""}
    )
    assert sem_token.status_code == 401
    assert publicador.publicados == []


def test_dispositivo_mostra_o_ultimo_comando(autenticado, db_session, tanque):
    id_dispositivo = _id_dispositivo(db_session, tanque)
    url = f"/tanques/{tanque.id}/dispositivos"
    assert autenticado.get(url).json()[0]["ultimo_acionamento"] is None

    autenticado.post(f"/dispositivos/{id_dispositivo}/aerador", json={"acao": "ligar"})
    desligar = autenticado.post(f"/dispositivos/{id_dispositivo}/aerador", json={"acao": "desligar"}).json()

    ultimo = autenticado.get(url).json()[0]["ultimo_acionamento"]
    assert ultimo == desligar | {"automatico": False}


def test_acionamento_ligado_a_previsao_conta_como_automatico(autenticado, db_session, tanque):
    gravar_ciclo(db_session, tanque, agora(), od=2.6, nivel_od="critico")
    id_previsao = db_session.scalar(select(Previsao.id).where(Previsao.horizonte_h == 0))
    db_session.add(
        AcionamentoAtuador(
            id_dispositivo=_id_dispositivo(db_session, tanque), id_tanque=tanque.id, id_previsao=id_previsao,
            acao="ligar", motivo="OD estimado abaixo de 3 mg/L.", ts_acionamento=agora(),
        )
    )
    db_session.commit()

    ultimo = autenticado.get(f"/tanques/{tanque.id}/dispositivos").json()[0]["ultimo_acionamento"]
    assert (ultimo["automatico"], ultimo["motivo"]) == (True, "OD estimado abaixo de 3 mg/L.")


def test_eventos_trazem_os_acionamentos_mais_recentes_primeiro(autenticado, db_session, tanque):
    id_dispositivo = _id_dispositivo(db_session, tanque)
    base = agora()
    for minutos, acao in [(30, "ligar"), (20, "desligar"), (10, "ligar")]:
        db_session.add(
            AcionamentoAtuador(
                id_dispositivo=id_dispositivo, id_tanque=tanque.id, acao=acao, motivo=None,
                ts_acionamento=base - timedelta(minutes=minutos),
            )
        )
    db_session.commit()

    pagina = autenticado.get("/eventos", params={"por_pagina": 2}).json()
    assert pagina["total"] == 3 and pagina["pagina"] == 1
    [primeiro, segundo] = pagina["itens"]
    assert primeiro["tipo"] == "acionamento" and primeiro["id"].startswith("acionamento-")
    assert (primeiro["acao"], segundo["acao"]) == ("ligar", "desligar")
    assert primeiro["tanque_nome"] == "Tanque bancada TCC" and primeiro["automatico"] is False
    assert len(autenticado.get("/eventos", params={"pagina": 2, "por_pagina": 2}).json()["itens"]) == 1
