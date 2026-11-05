import pytest

from src.api.usuarios import definir_usuario
from src.db.models import Configuracao
from tests.api.fabricas import SENHA

URL = "https://n8n.exemplo.test/webhook/abc-123"
CAMINHO = "/configuracoes/alertas"


def test_sem_configuracao_devolve_vazio(autenticado):
    resposta = autenticado.get(CAMINHO)
    assert resposta.status_code == 200
    assert resposta.json() == {"webhook_url": None, "atualizado_em": None}


def test_salva_e_le_a_url(autenticado, db_session):
    resposta = autenticado.put(CAMINHO, json={"webhook_url": f"  {URL} "})
    assert resposta.status_code == 200
    assert resposta.json()["webhook_url"] == URL
    assert resposta.json()["atualizado_em"] is not None

    assert autenticado.get(CAMINHO).json()["webhook_url"] == URL
    assert db_session.get(Configuracao, "alertas_webhook_url").valor == URL


def test_trocar_a_url_mantem_uma_linha_so(autenticado):
    autenticado.put(CAMINHO, json={"webhook_url": URL})
    autenticado.put(CAMINHO, json={"webhook_url": "http://localhost:5678/webhook/outro"})
    assert autenticado.get(CAMINHO).json()["webhook_url"] == "http://localhost:5678/webhook/outro"


@pytest.mark.parametrize("vazio", [None, "", "   "])
def test_url_vazia_desliga_os_alertas(autenticado, db_session, vazio):
    autenticado.put(CAMINHO, json={"webhook_url": URL})
    resposta = autenticado.put(CAMINHO, json={"webhook_url": vazio})
    assert resposta.status_code == 200
    assert resposta.json() == {"webhook_url": None, "atualizado_em": None}
    db_session.expire_all()
    assert db_session.get(Configuracao, "alertas_webhook_url") is None


@pytest.mark.parametrize(
    "invalida",
    ["n8n.exemplo.test/webhook", "ftp://n8n.exemplo.test/x", "https://", "javascript:alert(1)", "https://a b.test/x", "http://[invalido"],
)
def test_recusa_url_invalida_sem_gravar(autenticado, invalida):
    resposta = autenticado.put(CAMINHO, json={"webhook_url": invalida})
    assert resposta.status_code == 422
    assert "URL completa" in str(resposta.json())
    assert autenticado.get(CAMINHO).json()["webhook_url"] is None


def test_recusa_url_longa_demais(autenticado):
    resposta = autenticado.put(CAMINHO, json={"webhook_url": "https://a.test/" + "x" * 500})
    assert resposta.status_code == 422


@pytest.mark.parametrize("metodo", ["GET", "PUT"])
def test_so_administrador_ve_ou_altera(cliente, db_session, metodo):
    definir_usuario(db_session, "produtor@teste.local", SENHA, nome="Produtor", perfil="operador")
    db_session.commit()
    token = cliente.post("/auth/login", json={"email": "produtor@teste.local", "senha": SENHA}).json()["access_token"]

    resposta = cliente.request(metodo, CAMINHO, json={"webhook_url": URL}, headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 403


def test_sem_login_nao_acessa(cliente):
    assert cliente.get(CAMINHO).status_code == 401
