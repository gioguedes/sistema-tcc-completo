from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from src.api.rotas import cadastro
from src.api.usuarios import definir_usuario
from src.db.models import Dispositivo, Sensor, Tanque
from src.mqtt.processor import LeituraProcessor
from src.mqtt.schemas import LeituraMqttPayload
from tests.api.fabricas import SENHA

MAC_NOVO = "a4:f0:0f:64:3c:99"
MAC_REPETIDO = "Este endereço MAC já está cadastrado em outro dispositivo."


def _dados_tanque(tanque_seed: Tanque, **sobrescritas) -> dict:
    dados = {
        "nome": "Tanque Norte",
        "id_especie": tanque_seed.id_especie,
        "volume_litros": 500,
        "quantidade_peixes": 40,
        "data_povoamento": "2026-08-10",
        "status": "ativo",
    }
    return dados | sobrescritas


def _dados_dispositivo(**sobrescritas) -> dict:
    dados = {
        "nome": "No sensor Norte",
        "mac_address": "A4-F0-0F-64-3C-99",
        "modelo_esp32": "ESP32 DevKitC V4",
        "versao_firmware": "1.2.0",
        "ip_local": "192.168.0.21",
    }
    return dados | sobrescritas


def _erros(resposta) -> dict[tuple, tuple[str, str]]:
    return {tuple(e["loc"]): (e["msg"], e["type"]) for e in resposta.json()["detail"]}


def _total(db_session, modelo) -> int:
    return db_session.scalar(select(func.count()).select_from(modelo))


def test_cria_tanque_sem_dispositivo(autenticado, tanque):
    resposta = autenticado.post("/tanques", json=_dados_tanque(tanque, data_povoamento=None))

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Tanque Norte"
    assert corpo["volume_litros"] == "500.00"
    assert corpo["data_povoamento"] is None
    assert corpo["especie"]["id"] == tanque.id_especie
    assert corpo["dispositivos"] == [] and corpo["ultimas_leituras"] == []
    assert corpo["nivel_risco"] is None


def test_cria_tanque_com_dispositivo_e_os_tres_sensores_na_mesma_transacao(autenticado, db_session, tanque):
    resposta = autenticado.post("/tanques", json=_dados_tanque(tanque, dispositivo=_dados_dispositivo()))

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    [resumo] = corpo["dispositivos"]
    assert resumo["status_conexao"] == "offline"

    [dispositivo] = autenticado.get(f"/tanques/{corpo['id']}/dispositivos").json()
    assert dispositivo["mac_address"] == MAC_NOVO  # normalizado como a ingestao procura
    assert dispositivo["ip_local"] == "192.168.0.21"
    assert sorted((s["grandeza"], s["status"]) for s in dispositivo["sensores"]) == [
        ("ph", "ativo"), ("temperatura", "ativo"), ("turbidez", "ativo"),
    ]
    sensores = db_session.scalars(select(Sensor).where(Sensor.id_dispositivo == dispositivo["id"])).all()
    assert {s.id_tanque for s in sensores} == {corpo["id"]}


def test_dispositivo_cadastrado_pela_api_ja_recebe_leituras_da_ingestao(autenticado, db_session, tanque):
    autenticado.post("/tanques", json=_dados_tanque(tanque, dispositivo=_dados_dispositivo()))

    payload = LeituraMqttPayload(mac="a4f00f643c99", ts=1791590400, ph=7.1, temperatura=26.0, turbidez=None)
    assert LeituraProcessor().processar_payload(db_session, payload) == 2


def test_modelo_vazio_usa_o_padrao_e_opcionais_vazios_viram_nulos(autenticado, tanque):
    dispositivo = _dados_dispositivo(modelo_esp32="", versao_firmware=" ", ip_local="")
    corpo = autenticado.post("/tanques", json=_dados_tanque(tanque, dispositivo=dispositivo)).json()

    [d] = autenticado.get(f"/tanques/{corpo['id']}/dispositivos").json()
    assert (d["modelo_esp32"], d["versao_firmware"], d["ip_local"]) == ("ESP32 DevKitC V4", None, None)


def test_mac_repetido_da_409_e_nao_grava_nem_o_tanque(autenticado, db_session, tanque):
    antes = _total(db_session, Tanque)
    # o MAC do no do seed, escrito de outro jeito
    dispositivo = _dados_dispositivo(mac_address="A4F00F643C70")
    resposta = autenticado.post("/tanques", json=_dados_tanque(tanque, dispositivo=dispositivo))

    assert resposta.status_code == 409
    assert _erros(resposta) == {("body", "dispositivo", "mac_address"): (MAC_REPETIDO, "conflict")}
    assert _total(db_session, Tanque) == antes


def test_mac_gravado_por_outra_requisicao_depois_da_checagem_tambem_da_409(
    autenticado, db_session, tanque, monkeypatch
):
    # simula a corrida: a checagem previa nao ve o MAC e o banco recusa no INSERT (uq_disp_mac)
    monkeypatch.setattr(cadastro, "_checar_mac", lambda *args, **kwargs: None)
    antes = _total(db_session, Tanque)
    dispositivo = _dados_dispositivo(mac_address="a4:f0:0f:64:3c:70")
    resposta = autenticado.post("/tanques", json=_dados_tanque(tanque, dispositivo=dispositivo))

    assert resposta.status_code == 409
    assert _erros(resposta) == {("body", "dispositivo", "mac_address"): (MAC_REPETIDO, "conflict")}
    assert _total(db_session, Tanque) == antes


def test_validacao_do_tanque_e_do_dispositivo_em_portugues(autenticado, tanque):
    amanha = (date.today() + timedelta(days=2)).isoformat()
    dados = _dados_tanque(
        tanque,
        nome="  ",
        volume_litros=0,
        quantidade_peixes=-1,
        data_povoamento=amanha,
        dispositivo=_dados_dispositivo(nome="", mac_address="xyz", ip_local="999.1.1.1"),
    )
    resposta = autenticado.post("/tanques", json=dados)

    assert resposta.status_code == 422
    assert {campo: msg for campo, (msg, _) in _erros(resposta).items()} == {
        ("body", "nome"): "Informe o nome do tanque.",
        ("body", "volume_litros"): "O volume deve ser maior que zero.",
        ("body", "quantidade_peixes"): "A quantidade não pode ser negativa.",
        ("body", "data_povoamento"): "A data não pode estar no futuro.",
        ("body", "dispositivo", "nome"): "Informe o nome do dispositivo.",
        ("body", "dispositivo", "mac_address"): "Use o formato AA:BB:CC:DD:EE:FF.",
        ("body", "dispositivo", "ip_local"): "Informe um IP válido, como 192.168.0.20.",
    }


def test_especie_fora_do_catalogo(autenticado, tanque):
    resposta = autenticado.post("/tanques", json=_dados_tanque(tanque, id_especie=999999))
    assert resposta.status_code == 422
    assert _erros(resposta) == {("body", "id_especie"): ("Selecione uma espécie do catálogo.", "value_error")}


def test_edita_tanque(autenticado, tanque):
    dados = _dados_tanque(tanque, nome="Tanque bancada", quantidade_peixes=12, status="inativo")
    resposta = autenticado.patch(f"/tanques/{tanque.id}", json=dados)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["nome"], corpo["quantidade_peixes"], corpo["status"]) == ("Tanque bancada", 12, "inativo")
    # o dispositivo continua ligado ao tanque: inativar nao apaga nada (I-08)
    assert len(corpo["dispositivos"]) == 1
    assert autenticado.patch("/tanques/999999", json=dados).status_code == 404


def test_cria_dispositivo_em_tanque_existente(autenticado, tanque):
    resposta = autenticado.post("/dispositivos", json=_dados_dispositivo(id_tanque=tanque.id))

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["id_tanque"] == tanque.id and corpo["mac_address"] == MAC_NOVO
    assert len(corpo["sensores"]) == 3
    assert len(autenticado.get(f"/tanques/{tanque.id}/dispositivos").json()) == 2


def test_criar_dispositivo_valida_tanque_e_mac(autenticado, tanque):
    resposta = autenticado.post("/dispositivos", json=_dados_dispositivo(id_tanque=999999))
    assert _erros(resposta) == {("body", "id_tanque"): ("Tanque não encontrado.", "value_error")}

    resposta = autenticado.post(
        "/dispositivos", json=_dados_dispositivo(id_tanque=tanque.id, mac_address="a4:f0:0f:64:3c:70")
    )
    assert resposta.status_code == 409
    assert _erros(resposta) == {("body", "mac_address"): (MAC_REPETIDO, "conflict")}


def test_edita_dispositivo(autenticado, db_session, tanque):
    id_seed = db_session.scalar(select(Dispositivo.id).where(Dispositivo.id_tanque == tanque.id))
    novo = autenticado.post("/dispositivos", json=_dados_dispositivo(id_tanque=tanque.id)).json()

    # manter o proprio MAC nao e conflito
    resposta = autenticado.patch(
        f"/dispositivos/{id_seed}",
        json=_dados_dispositivo(nome="No da bancada", mac_address="a4:f0:0f:64:3c:70", modelo_esp32=""),
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert (corpo["nome"], corpo["modelo_esp32"], corpo["versao_firmware"]) == (
        "No da bancada", "ESP32 DevKitC V4", "1.2.0",
    )

    resposta = autenticado.patch(f"/dispositivos/{id_seed}", json=_dados_dispositivo(mac_address=novo["mac_address"]))
    assert resposta.status_code == 409
    assert autenticado.patch("/dispositivos/999999", json=_dados_dispositivo()).status_code == 404


def test_altera_status_do_sensor(autenticado, db_session, tanque):
    sensor = db_session.scalar(select(Sensor).where(Sensor.id_tanque == tanque.id).order_by(Sensor.id))

    resposta = autenticado.patch(f"/sensores/{sensor.id}", json={"status": "em_calibracao"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "em_calibracao"
    assert resposta.json()["modelo"] in {"SEN0161-V2", "DS18B20", "SEN0189"}

    assert autenticado.patch(f"/sensores/{sensor.id}", json={"status": "quebrado"}).status_code == 422
    assert autenticado.patch("/sensores/999999", json={"status": "ativo"}).status_code == 404


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("post", "/tanques"),
        ("patch", "/tanques/1"),
        ("post", "/dispositivos"),
        ("patch", "/dispositivos/1"),
        ("patch", "/sensores/1"),
    ],
)
def test_cadastro_e_so_para_administrador(cliente, db_session, tanque, metodo, caminho):
    definir_usuario(db_session, "produtor@teste.local", SENHA, nome="Produtor", perfil="operador")
    db_session.commit()
    token = cliente.post("/auth/login", json={"email": "produtor@teste.local", "senha": SENHA}).json()["access_token"]

    resposta = cliente.request(metodo, caminho, json={}, headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso restrito a administradores."}
