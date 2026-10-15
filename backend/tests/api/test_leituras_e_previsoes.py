from datetime import datetime, timedelta, timezone

from tests.api.fabricas import MINUTO, agora, gravar_ciclo, gravar_leituras

# blocos de 5 min e de 1 h alinhados, para as contas do teste serem exatas
BASE = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _periodo(desde: datetime, ate: datetime, **outros) -> dict:
    return {"desde": desde.isoformat(), "ate": ate.isoformat(), **outros}


def _series(resposta) -> dict[str, dict]:
    assert resposta.status_code == 200, resposta.text
    return {s["grandeza"]: s for s in resposta.json()["series"]}


def test_leituras_brutas(autenticado, db_session, tanque):
    for i, ph in enumerate([7.0, 7.1, 7.2]):
        gravar_leituras(db_session, tanque, BASE + i * MINUTO, ph=ph, temperatura=25.0 + i)
    gravar_leituras(db_session, tanque, BASE + 2 * timedelta(hours=1), ph=9.9)  # fora do periodo
    db_session.commit()

    resposta = autenticado.get(
        f"/tanques/{tanque.id}/leituras",
        params=_periodo(BASE, BASE + timedelta(hours=1), bucket="raw", grandezas="ph,temperatura"),
    )
    series = _series(resposta)

    assert list(series) == ["ph", "temperatura"]
    assert series["ph"]["unidade"] == "pH" and series["ph"]["estimado"] is False
    # bruto: sem min/max
    assert series["ph"]["pontos"] == [
        {"ts": "2026-10-09T12:00:00Z", "valor": "7.0000"},
        {"ts": "2026-10-09T12:01:00Z", "valor": "7.1000"},
        {"ts": "2026-10-09T12:02:00Z", "valor": "7.2000"},
    ]


def test_leituras_agregadas_em_5_min(autenticado, db_session, tanque):
    for i, ph in enumerate([7.0, 7.2, 7.4, 7.6, 7.8, 8.0]):  # 12:00 a 12:05
        gravar_leituras(db_session, tanque, BASE + i * MINUTO, ph=ph)
    db_session.commit()

    series = _series(
        autenticado.get(
            f"/tanques/{tanque.id}/leituras",
            params=_periodo(BASE, BASE + timedelta(hours=1), bucket="5m", grandezas="ph"),
        )
    )

    assert series["ph"]["pontos"] == [
        {"ts": "2026-10-09T12:00:00Z", "valor": "7.4000", "min": "7.0000", "max": "7.8000"},
        {"ts": "2026-10-09T12:05:00Z", "valor": "8.0000", "min": "8.0000", "max": "8.0000"},
    ]


def test_serie_de_od_vem_das_estimativas_do_ml(autenticado, db_session, tanque):
    for i, od in enumerate([6.0, 5.0, 4.0]):  # um ciclo a cada 5 min
        gravar_ciclo(db_session, tanque, BASE + 5 * i * MINUTO, od=od)
    db_session.commit()
    url = f"/tanques/{tanque.id}/leituras"

    od = _series(autenticado.get(url, params=_periodo(BASE, BASE + timedelta(hours=1), grandezas="od")))["od"]
    assert od["estimado"] is True and od["unidade"] == "mg/L"
    assert [p["valor"] for p in od["pontos"]] == ["6.0000", "5.0000", "4.0000"]

    por_hora = _series(
        autenticado.get(url, params=_periodo(BASE, BASE + timedelta(days=2), bucket="1h", grandezas="od"))
    )["od"]
    assert por_hora["pontos"] == [{"ts": "2026-10-09T12:00:00Z", "valor": "5.0000", "min": "4.0000", "max": "6.0000"}]


def test_todas_as_grandezas_por_padrao(autenticado, tanque):
    series = _series(
        autenticado.get(f"/tanques/{tanque.id}/leituras", params=_periodo(BASE, BASE + timedelta(hours=1)))
    )
    assert list(series) == ["ph", "temperatura", "turbidez", "od"]
    assert all(s["pontos"] == [] for s in series.values())


def test_validacao_do_periodo(autenticado, tanque):
    url = f"/tanques/{tanque.id}/leituras"
    casos = [
        (_periodo(BASE, BASE), "desde"),
        (_periodo(BASE, BASE + timedelta(days=30), bucket="raw"), "bucket"),
        (_periodo(BASE, BASE + timedelta(hours=1), grandezas="ph,amonia"), "grandezas"),
    ]
    for parametros, campo in casos:
        resposta = autenticado.get(url, params=parametros)
        assert resposta.status_code == 422, parametros
        assert resposta.json()["detail"][0]["loc"] == ["query", campo]

    assert autenticado.get(url, params={"desde": BASE.isoformat()}).status_code == 422
    assert autenticado.get("/tanques/999999/leituras", params=_periodo(BASE, BASE + MINUTO)).status_code == 404


def test_previsao_atual(autenticado, db_session, tanque):
    t = agora()
    gravar_leituras(db_session, tanque, t - MINUTO, ph=7.5, temperatura=26.0)
    gravar_ciclo(db_session, tanque, t - 10 * MINUTO, od=6.5)  # ciclo anterior
    gravar_ciclo(db_session, tanque, t - 5 * MINUTO, od=4.2, nivel_od="atencao", confianca_od=0.82)
    db_session.commit()

    corpo = autenticado.get(f"/tanques/{tanque.id}/previsoes/atual").json()

    assert corpo["nivel_risco"] == "atencao"
    assert corpo["gerada_em"] == (t - 5 * MINUTO).isoformat().replace("+00:00", "Z")
    assert corpo["od_atual"] == {
        "valor": "4.2000", "nivel_risco": "atencao", "confianca": "0.8200", "baixa_confianca": False,
    }
    assert [(h["horizonte_h"], h["nivel_risco"], h["parametro_critico"]) for h in corpo["horizontes"]] == [
        (1, "otimo", "ph"), (2, "atencao", "ph"), (3, "critico", "ph"),
    ]
    assert corpo["horizontes"][0]["confianca"] == "0.9000"
    assert corpo["horizontes"][0]["baixa_confianca"] is False


def test_previsao_indeterminada_quando_o_ml_nao_gravou(autenticado, tanque):
    corpo = autenticado.get(f"/tanques/{tanque.id}/previsoes/atual").json()
    assert corpo == {"id_tanque": tanque.id, "nivel_risco": None, "gerada_em": None, "od_atual": None, "horizontes": []}


def test_previsao_desatualizada_mantem_a_hora_do_ultimo_ciclo(autenticado, db_session, tanque):
    gerada = agora() - 20 * MINUTO
    gravar_ciclo(db_session, tanque, gerada)
    db_session.commit()

    corpo = autenticado.get(f"/tanques/{tanque.id}/previsoes/atual").json()
    assert corpo["nivel_risco"] is None and corpo["od_atual"] is None and corpo["horizontes"] == []
    assert corpo["gerada_em"] == gerada.isoformat().replace("+00:00", "Z")


def test_previsao_de_tanque_fora_de_operacao_nao_tem_data(autenticado, db_session, tanque):
    gravar_ciclo(db_session, tanque, agora() - MINUTO)
    tanque.status = "inativo"
    db_session.commit()

    corpo = autenticado.get(f"/tanques/{tanque.id}/previsoes/atual").json()
    assert corpo["gerada_em"] is None and corpo["nivel_risco"] is None
