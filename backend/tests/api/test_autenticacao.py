from src.api.rotas.autenticacao import COOKIE_RENOVACAO
from src.db.seed import semear
from tests.api.fabricas import SENHA


def _cookie(resposta) -> str:
    return resposta.headers["set-cookie"]


def test_login_devolve_token_e_cookie_de_renovacao(cliente, usuario):
    resposta = cliente.post("/auth/login", json={"email": "ADMIN@teste.local ", "senha": SENHA})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["access_token"] and corpo["expira_em"]
    cookie = _cookie(resposta)
    assert cookie.startswith(f"{COOKIE_RENOVACAO}=")
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/api/v1/auth" in cookie
    # sem "lembrar de mim": cookie de sessao
    assert "Max-Age" not in cookie


def test_lembrar_de_mim_deixa_o_cookie_persistente(cliente, usuario):
    resposta = cliente.post("/auth/login", json={"email": usuario.email, "senha": SENHA, "lembrar": True})
    assert "Max-Age=2592000" in _cookie(resposta)


def test_cookie_e_secure_por_padrao(cliente, usuario, config):
    config.api_cookie_seguro = True
    resposta = cliente.post("/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert "Secure" in _cookie(resposta)


def test_login_com_senha_errada_ou_email_desconhecido_da_401(cliente, usuario):
    for email, senha in [(usuario.email, "outra-senha"), ("ninguem@teste.local", SENHA)]:
        resposta = cliente.post("/auth/login", json={"email": email, "senha": senha})
        assert resposta.status_code == 401
        assert resposta.json() == {"detail": "E-mail ou senha incorretos."}


def test_usuario_do_seed_sem_senha_nao_entra(cliente, db_session):
    semear(db_session)
    db_session.commit()
    resposta = cliente.post(
        "/auth/login", json={"email": "operador@piscicultura.local", "senha": "sem-autenticacao-neste-sub-projeto"}
    )
    assert resposta.status_code == 401


def test_rotas_protegidas_exigem_token(cliente):
    for caminho in ("/auth/eu", "/tanques", "/especies", "/alertas"):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 401, caminho
    assert cliente.get("/auth/eu", headers={"Authorization": "Bearer invalido"}).status_code == 401


def test_eu_devolve_o_usuario_sem_senha(autenticado):
    corpo = autenticado.get("/auth/eu").json()
    assert corpo == {
        "id": corpo["id"], "nome": "Admin Teste", "email": "admin@teste.local", "telefone": None, "perfil": "admin",
    }


def test_refresh_usa_o_cookie_e_o_token_de_renovacao_nao_serve_de_acesso(cliente, usuario):
    cliente.post("/auth/login", json={"email": usuario.email, "senha": SENHA})
    renovacao = cliente.cookies[COOKIE_RENOVACAO]

    resposta = cliente.post("/auth/refresh")
    assert resposta.status_code == 200
    novo = resposta.json()["access_token"]
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {novo}"}).status_code == 200
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {renovacao}"}).status_code == 401


def test_refresh_sem_cookie_da_401(cliente):
    resposta = cliente.post("/auth/refresh")
    assert resposta.status_code == 401


def test_logout_apaga_o_cookie(cliente, usuario):
    cliente.post("/auth/login", json={"email": usuario.email, "senha": SENHA})
    resposta = cliente.post("/auth/logout")

    assert resposta.status_code == 204
    assert 'renovacao=""' in _cookie(resposta) and "Max-Age=0" in _cookie(resposta)
    assert cliente.post("/auth/refresh").status_code == 401


def test_atualizar_conta(autenticado):
    resposta = autenticado.patch("/auth/eu", json={"nome": "  Marina Souza ", "telefone": "+5511987654321"})
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Marina Souza"
    assert resposta.json()["telefone"] == "+5511987654321"

    resposta = autenticado.patch("/auth/eu", json={"nome": "Marina Souza", "telefone": None})
    assert resposta.json()["telefone"] is None


def test_atualizar_conta_valida_os_campos_em_portugues(autenticado):
    resposta = autenticado.patch("/auth/eu", json={"nome": " ", "telefone": "1234"})

    assert resposta.status_code == 422
    erros = {tuple(e["loc"]): e["msg"] for e in resposta.json()["detail"]}
    assert erros == {
        ("body", "nome"): "Informe seu nome.",
        ("body", "telefone"): "Informe DDD e número, como (11) 98765-4321.",
    }
