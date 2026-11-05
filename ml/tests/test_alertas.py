import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from sqlalchemy import text

from src.faixas import TILAPIA
from src.servico.alertas import CASOS, MonitorAlertas, Webhook, alerta_simulado, classificar
from tests.banco import inserir_leituras, semear_tanque

INICIO = datetime(2026, 11, 23, 19, 0, 0, tzinfo=timezone.utc)
CONFIANCA_MIN = 0.5


class DestinoFalso:
    def __init__(self) -> None:
        self.recebidos: list[dict] = []
        self.responde = True

    def enviar(self, alerta: dict) -> bool:
        self.recebidos.append(alerta)
        return self.responde

    @property
    def casos(self) -> list[str]:
        return [a["caso"] for a in self.recebidos]


class Cenario:
    """Publica uma leitura por minuto e roda um ciclo do monitor logo depois de cada uma."""

    def __init__(self, db, destino: DestinoFalso) -> None:
        self.db = db
        self.monitor = MonitorAlertas(destino, CONFIANCA_MIN)
        with db.begin() as conn:
            self.ids = semear_tanque(conn)
        self.agora = INICIO

    def leitura(self, ph: float, temperatura: float = 26.0) -> dict:
        with self.db.begin() as conn:
            inserir_leituras(conn, self.ids["sensores"]["ph"], self.agora, [ph])
            inserir_leituras(conn, self.ids["sensores"]["temperatura"], self.agora, [temperatura])
        contagem = self.monitor.executar_ciclo(self.db, self.agora + timedelta(seconds=5))
        self.agora += timedelta(minutes=1)
        return contagem

    def linhas_alertas(self):
        with self.db.connect() as conn:
            return conn.execute(text("SELECT status, ts_envio, canal, mensagem FROM alertas ORDER BY id")).all()

    def previsao_od(self, valor: float, confianca: float) -> None:
        with self.db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO previsoes (id_tanque, parametro_critico, valor_previsto, nivel_risco, horizonte_h, confianca, ts_previsao) "
                    "VALUES (:t, 'od', :v, :n, 0, :c, :ts)"
                ),
                {"t": self.ids["id_tanque"], "v": valor, "n": "critico" if valor < 4 else "otimo", "c": confianca, "ts": self.agora},
            )


@pytest.fixture()
def destino():
    return DestinoFalso()


@pytest.fixture()
def cenario(db, destino):
    return Cenario(db, destino)


@pytest.mark.parametrize(
    ("ph", "temperatura", "esperado"),
    [
        (8.1, 26.0, "normal"),
        (8.5, 26.0, "normal"),  # a borda ainda é atenção, não crítico
        (6.5, 26.0, "normal"),
        (8.51, 26.0, "ph_alto"),
        (9.18, 26.0, "ph_alto"),
        (6.49, 26.0, "ph_baixo"),
        (4.2, 26.0, "ph_baixo"),
        (7.5, 30.5, "temperatura_alta"),
        (7.5, 19.5, "temperatura_baixa"),
    ],
)
def test_classifica_pelos_limites_da_especie(ph, temperatura, esperado):
    assert classificar({"ph": [ph], "temperatura": [temperatura]}, None, TILAPIA, CONFIANCA_MIN, None) == esperado


def test_sem_leitura_recente_nao_ha_caso():
    assert classificar({}, (2.0, 0.9), TILAPIA, CONFIANCA_MIN, None) is None


def test_od_critico_so_vale_com_confianca():
    leituras = {"ph": [7.5], "temperatura": [26.0]}
    assert classificar(leituras, (3.0, 0.8), TILAPIA, CONFIANCA_MIN, None) == "od_baixo"
    assert classificar(leituras, (3.0, 0.0), TILAPIA, CONFIANCA_MIN, None) == "normal"


def test_ph_medido_vem_antes_do_od_estimado():
    assert classificar({"ph": [9.18], "temperatura": [26.0]}, (3.0, 0.8), TILAPIA, CONFIANCA_MIN, None) == "ph_alto"


def test_demonstracao_dos_tres_copos_dispara_uma_vez_por_mudanca(cenario, destino):
    for ph in (8.1, 8.1, 8.1):  # torneira
        cenario.leitura(ph)
    assert destino.casos == ["normal"]

    for ph in (9.18, 9.18, 9.18):  # tampão
        cenario.leitura(ph)
    assert destino.casos == ["normal", "ph_alto"]

    for ph in (4.2, 4.2):  # vinagre, direto do tampão: muda na hora
        cenario.leitura(ph)
    assert destino.casos == ["normal", "ph_alto", "ph_baixo"]


def test_alerta_sai_na_primeira_leitura_critica(cenario, destino):
    cenario.leitura(8.1)
    assert cenario.leitura(9.18) == {"enviados": 1, "falhas": 0}
    assert destino.casos[-1] == "ph_alto"


def test_uma_leitura_de_volta_a_faixa_nao_encerra_o_critico(cenario, destino):
    for ph in (9.18, 8.1):
        cenario.leitura(ph)
    assert destino.casos == ["ph_alto"]
    cenario.leitura(8.1)
    assert destino.casos == ["ph_alto", "normal"]


def test_sensor_oscilando_na_borda_nao_gera_um_alerta_por_minuto(cenario, destino):
    for ph in (8.6, 8.4, 8.6, 8.4, 8.6, 8.4):
        cenario.leitura(ph)
    assert destino.casos == ["ph_alto"]


def test_grava_o_alerta_como_enviado_no_canal_whatsapp(cenario):
    cenario.leitura(9.18)
    linha = cenario.linhas_alertas()[0]
    assert (linha.status, linha.canal) == ("enviado", "whatsapp")
    assert linha.ts_envio is not None
    assert "9,18" in linha.mensagem


def test_falha_no_webhook_tenta_de_novo_na_mesma_linha(cenario, destino):
    destino.responde = False
    assert cenario.leitura(9.18) == {"enviados": 0, "falhas": 1}
    linhas = cenario.linhas_alertas()
    assert [(l.status, l.ts_envio) for l in linhas] == [("falha", None)]

    assert cenario.leitura(9.18) == {"enviados": 0, "falhas": 1}
    assert len(cenario.linhas_alertas()) == 1

    destino.responde = True
    assert cenario.leitura(9.18) == {"enviados": 1, "falhas": 0}
    linhas = cenario.linhas_alertas()
    assert [l.status for l in linhas] == ["enviado"]
    assert destino.casos == ["ph_alto"] * 3
    cenario.leitura(9.18)
    assert len(destino.casos) == 3


def test_falha_seguida_de_outro_caso_registra_os_dois(cenario, destino):
    destino.responde = False
    cenario.leitura(9.18)
    destino.responde = True
    cenario.leitura(4.2)
    assert [l.status for l in cenario.linhas_alertas()] == ["falha", "enviado"]


def test_no_parado_nao_dispara(cenario, destino):
    cenario.leitura(8.1)
    cenario.monitor.executar_ciclo(cenario.db, cenario.agora + timedelta(minutes=30))
    assert destino.casos == ["normal"]


def test_payload_tem_o_que_o_workflow_precisa(cenario, destino):
    cenario.previsao_od(6.5, 0.8)
    cenario.leitura(9.18)
    alerta = destino.recebidos[0]
    assert alerta["evento"] == "alerta_qualidade_agua"
    assert alerta["simulado"] is False
    assert alerta["caso"] == "ph_alto"
    assert alerta["nivel_risco"] == "critico"
    assert alerta["parametro"] == "ph"
    assert alerta["valor"] == pytest.approx(9.18)
    assert (alerta["faixa_min"], alerta["faixa_max"]) == (6.5, 8.5)
    assert alerta["id_tanque"] == cenario.ids["id_tanque"]
    assert alerta["od_estimado"] == pytest.approx(6.5)
    assert alerta["od_confianca"] == pytest.approx(0.8)
    assert alerta["recomendacao"]
    assert "acima do limite de 8,5" in alerta["mensagem"]
    json.dumps(alerta)


def test_mensagem_do_od_deixa_claro_que_e_estimado(cenario, destino):
    cenario.previsao_od(3.0, 0.8)
    cenario.leitura(7.5)
    assert destino.casos == ["od_baixo"]
    assert "OD estimado" in destino.recebidos[0]["mensagem"]


@pytest.mark.parametrize("caso", CASOS)
def test_exemplo_simulado_de_cada_caso(caso):
    agora = datetime(2026, 11, 23, tzinfo=timezone.utc)
    alerta = alerta_simulado(caso, TILAPIA, agora)
    assert alerta["caso"] == caso
    assert alerta["simulado"] is True
    assert alerta["id_alerta"] == 0
    # o exemplo precisa bater com a classificação real, senão o workflow é montado em cima de um caso impossível
    assert classificar(
        {"ph": [alerta["ph"]], "temperatura": [alerta["temperatura"]]},
        (alerta["od_estimado"], alerta["od_confianca"]),
        TILAPIA,
        CONFIANCA_MIN,
        None,
    ) == caso
    json.dumps(alerta)


class _Servidor:
    def __init__(self, status: int = 200) -> None:
        recebidos = self.recebidos = []

        class Tratador(BaseHTTPRequestHandler):
            def do_POST(self):
                corpo = self.rfile.read(int(self.headers["Content-Length"]))
                recebidos.append((self.headers.get("Authorization"), self.headers.get("Content-Type"), json.loads(corpo)))
                self.send_response(status)
                self.end_headers()

            def log_message(self, *args):
                pass

        self._http = HTTPServer(("127.0.0.1", 0), Tratador)
        self.url = f"http://127.0.0.1:{self._http.server_port}/webhook/alerta"
        threading.Thread(target=self._http.serve_forever, daemon=True).start()

    def fechar(self) -> None:
        self._http.shutdown()
        self._http.server_close()


def test_webhook_envia_json_com_acento_e_token():
    servidor = _Servidor()
    try:
        assert Webhook(servidor.url, "segredo").enviar({"mensagem": "água crítica"}) is True
    finally:
        servidor.fechar()
    assert servidor.recebidos == [("Bearer segredo", "application/json", {"mensagem": "água crítica"})]


def test_webhook_sem_token_nao_manda_o_cabecalho():
    servidor = _Servidor()
    try:
        assert Webhook(servidor.url).enviar({}) is True
    finally:
        servidor.fechar()
    assert servidor.recebidos[0][0] is None


@pytest.mark.parametrize("status", [404, 500])
def test_resposta_de_erro_conta_como_falha(status):
    servidor = _Servidor(status)
    try:
        assert Webhook(servidor.url).enviar({}) is False
    finally:
        servidor.fechar()


def test_servidor_fora_do_ar_conta_como_falha_e_nao_expoe_a_url(caplog):
    servidor = _Servidor()
    url = servidor.url
    servidor.fechar()
    assert Webhook(url).enviar({}) is False
    assert url not in caplog.text
