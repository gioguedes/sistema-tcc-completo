from src.db.models import Tanque
from tests.api.fabricas import MINUTO, agora, gravar_ciclo, gravar_leituras


def _tanque(cliente, tanque: Tanque) -> dict:
    resposta = cliente.get(f"/tanques/{tanque.id}")
    assert resposta.status_code == 200
    return resposta.json()


def _leituras(corpo: dict) -> dict[str, dict]:
    return {leitura["grandeza"]: leitura for leitura in corpo["ultimas_leituras"]}


def test_tanque_sem_dados(autenticado, tanque):
    corpo = _tanque(autenticado, tanque)

    assert corpo["nome"] == "Tanque bancada TCC"
    assert corpo["especie"]["nome_cientifico"] == "Oreochromis niloticus"
    assert corpo["especie"]["ph_min"] == "6.50"
    assert corpo["nivel_risco"] is None
    assert corpo["ultima_leitura_em"] is None
    assert corpo["ultimas_leituras"] == []
    assert [(d["nome"], d["status_conexao"]) for d in corpo["dispositivos"]] == [("No sensor bancada", "offline")]


def test_ultima_leitura_por_grandeza_e_od_estimado_do_ml(autenticado, db_session, tanque):
    t = agora()
    gravar_leituras(db_session, tanque, t - 10 * MINUTO, ph=7.0, temperatura=25.0, turbidez=30.0)
    # sensor de turbidez em falha: o no publica null e a ingestao nao grava
    gravar_leituras(db_session, tanque, t - MINUTO, ph=7.2, temperatura=26.0)
    gravar_ciclo(db_session, tanque, t - 2 * MINUTO, od=5.6, nivel_od="otimo", confianca_od=0.46)
    db_session.commit()

    corpo = _tanque(autenticado, tanque)
    leituras = _leituras(corpo)

    assert leituras["ph"]["valor"] == "7.2000"
    assert leituras["turbidez"]["valor"] == "30.0000"
    assert leituras["turbidez"]["ts"] < leituras["ph"]["ts"]
    assert leituras["temperatura"]["unidade"] == "C"
    assert leituras["od"] == {
        "grandeza": "od", "valor": "5.6000", "unidade": "mg/L", "ts": leituras["od"]["ts"],
        "estimado": True, "baixa_confianca": True,
    }
    assert corpo["dispositivos"][0]["status_conexao"] == "online"
    assert corpo["ultima_leitura_em"] == corpo["dispositivos"][0]["ultima_leitura_em"]


def test_nivel_atual_e_o_pior_entre_ph_temperatura_e_od(autenticado, db_session, tanque):
    t = agora()
    # pH 8,4: dentro da faixa, mas na margem de 10% -> atencao; OD otimo
    gravar_leituras(db_session, tanque, t - MINUTO, ph=8.4, temperatura=26.0)
    gravar_ciclo(db_session, tanque, t - MINUTO, nivel_od="otimo")
    db_session.commit()
    assert _tanque(autenticado, tanque)["nivel_risco"] == "atencao"

    gravar_ciclo(db_session, tanque, t, od=2.8, nivel_od="critico")
    db_session.commit()
    assert _tanque(autenticado, tanque)["nivel_risco"] == "critico"


def test_sem_previsao_recente_nao_ha_nivel_atual(autenticado, db_session, tanque):
    t = agora()
    gravar_leituras(db_session, tanque, t - MINUTO, ph=7.5, temperatura=26.0)
    gravar_ciclo(db_session, tanque, t - 16 * MINUTO)
    db_session.commit()

    corpo = _tanque(autenticado, tanque)
    assert corpo["nivel_risco"] is None
    # a ultima estimativa de OD continua visivel, com o ts dela, para o painel dizer ha quanto tempo
    assert _leituras(corpo)["od"]["estimado"] is True


def test_tanque_fora_de_operacao_nao_tem_nivel(autenticado, db_session, tanque):
    t = agora()
    gravar_leituras(db_session, tanque, t - MINUTO, ph=7.5, temperatura=26.0)
    gravar_ciclo(db_session, tanque, t - MINUTO)
    tanque.status = "manutencao"
    db_session.commit()

    assert _tanque(autenticado, tanque)["nivel_risco"] is None


def test_no_sem_leitura_ha_mais_de_5_min_fica_offline(autenticado, db_session, tanque):
    gravar_leituras(db_session, tanque, agora() - 6 * MINUTO, ph=7.5, temperatura=26.0, turbidez=10.0)
    db_session.commit()
    assert _tanque(autenticado, tanque)["dispositivos"][0]["status_conexao"] == "offline"


def test_lista_de_tanques(autenticado, tanque):
    resposta = autenticado.get("/tanques")
    assert resposta.status_code == 200
    assert [t["id"] for t in resposta.json()] == [tanque.id]


def test_tanque_inexistente(autenticado):
    resposta = autenticado.get("/tanques/999999")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Tanque não encontrado."}


def test_dispositivos_do_tanque_com_sensores(autenticado, db_session, tanque):
    gravar_leituras(db_session, tanque, agora() - MINUTO, ph=7.5)
    db_session.commit()

    resposta = autenticado.get(f"/tanques/{tanque.id}/dispositivos")
    assert resposta.status_code == 200
    [dispositivo] = resposta.json()
    assert dispositivo["mac_address"] == "a4:f0:0f:64:3c:70"
    assert dispositivo["status_conexao"] == "online"
    assert dispositivo["ip_local"] is None
    assert sorted(s["grandeza"] for s in dispositivo["sensores"]) == ["ph", "temperatura", "turbidez"]
    assert {s["status"] for s in dispositivo["sensores"]} == {"ativo"}


def test_especies(autenticado, tanque):
    [especie] = autenticado.get("/especies").json()
    assert especie["nome_comum"] == "Tilapia do Nilo"
    assert especie["od_min"] == "4.00"


def test_alertas_vem_vazios_ate_o_sub_projeto_4(autenticado):
    assert autenticado.get("/alertas", params={"ativos": "true"}).json() == {
        "itens": [], "total": 0, "pagina": 1, "por_pagina": 10,
    }
    assert autenticado.get("/alertas", params={"por_pagina": 51}).status_code == 422

