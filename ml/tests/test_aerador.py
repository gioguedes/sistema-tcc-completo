from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from src.faixas import TILAPIA
from src.servico.__main__ import executar_ciclo
from src.servico.aerador import ControleAerador, LimitesAerador, UltimoComando, decidir, topico_aerador
from src.servico.inferencia import Previsao
from tests.banco import semear_tanque

AGORA = datetime(2026, 10, 29, 12, 0, 30, tzinfo=timezone.utc)
LIMITES = LimitesAerador(liga_od=4.0, desliga_od=5.0, pausa_manual=timedelta(minutes=30), confianca_min=0.5)


def _previsoes(od: float, od_1h: float | None = None, confianca: float = 0.8) -> list[Previsao]:
    critico, valor = ("od", od_1h) if od_1h is not None else ("ph", 7.0)
    return [Previsao(0, "od", od, "otimo", confianca)] + [
        Previsao(h, critico, valor, "otimo", 0.9) for h in (1, 2, 3)
    ]


def _ultimo(acao: str, automatico: bool, minutos_atras: int = 60) -> UltimoComando:
    return UltimoComando(acao, automatico, AGORA - timedelta(minutes=minutos_atras))


# --- regra de decisão (histerese) ---


def test_liga_com_od_abaixo_do_limite():
    acao, motivo = decidir(_previsoes(3.8), None, LIMITES, AGORA)
    assert acao == "ligar"
    assert "3,8 mg/L" in motivo and len(motivo) <= 160


def test_liga_antes_da_queda_pelo_od_projetado_para_1_h():
    acao, motivo = decidir(_previsoes(4.6, od_1h=3.9), _ultimo("desligar", True), LIMITES, AGORA)
    assert acao == "ligar"
    assert "previsto em 1 h: 3,9" in motivo


def test_histerese_nao_desliga_entre_os_limites():
    assert decidir(_previsoes(4.5), _ultimo("ligar", True), LIMITES, AGORA) is None
    assert decidir(_previsoes(4.5), _ultimo("desligar", True), LIMITES, AGORA) is None


def test_desliga_o_que_ligou_quando_o_od_recupera():
    acao, _ = decidir(_previsoes(5.3), _ultimo("ligar", True), LIMITES, AGORA)
    assert acao == "desligar"


def test_nao_desliga_se_a_projecao_ainda_esta_abaixo():
    assert decidir(_previsoes(5.3, od_1h=4.7), _ultimo("ligar", True), LIMITES, AGORA) is None


def test_nao_desliga_aerador_ligado_a_mao():
    assert decidir(_previsoes(7.0), _ultimo("ligar", False, minutos_atras=120), LIMITES, AGORA) is None


def test_respeita_a_pausa_depois_de_comando_manual():
    assert decidir(_previsoes(3.0), _ultimo("desligar", False, minutos_atras=10), LIMITES, AGORA) is None
    acao, _ = decidir(_previsoes(3.0), _ultimo("desligar", False, minutos_atras=31), LIMITES, AGORA)
    assert acao == "ligar"


def test_nao_age_com_estimativa_de_baixa_confianca():
    assert decidir(_previsoes(3.0, confianca=0.3), None, LIMITES, AGORA) is None


def test_topico_igual_ao_da_api():
    assert topico_aerador("tcc", "A4:F0:0F:64:3C:70") == "tcc/a4f00f643c70/aerador"


# --- ciclo completo no banco de teste ---


class PublicadorFalso:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.enviados: list[tuple] = []

    def publicar_aerador(self, mac, acao, id_acionamento, ts):
        self.enviados.append((mac, acao, id_acionamento, ts))
        return self.ok


class InferenciaFixa:
    def __init__(self, previsoes: list[Previsao]) -> None:
        self._previsoes = previsoes

    def prever(self, janela, faixa, agora):
        return self._previsoes


def _acionamentos(conn) -> list:
    return conn.execute(
        text("SELECT acao, id_previsao, motivo FROM acionamentos_atuador ORDER BY id")
    ).all()


def _ciclo(db, previsoes, publicador):
    controle = ControleAerador(LIMITES, publicador)
    return executar_ciclo(db, InferenciaFixa(previsoes), confianca_min=0.5, agora=AGORA, aerador=controle)


def test_ciclo_liga_registra_ligado_a_previsao_e_publica(db):
    with db.begin() as conn:
        semear_tanque(conn, TILAPIA)
    publicador = PublicadorFalso()
    assert _ciclo(db, _previsoes(3.5), publicador)["aerador"] == 1
    with db.connect() as conn:
        linhas = _acionamentos(conn)
        id_od = conn.execute(text("SELECT id FROM previsoes WHERE horizonte_h = 0")).scalar_one()
    assert [(l.acao, l.id_previsao) for l in linhas] == [("ligar", id_od)]
    assert publicador.enviados[0][:2] == ("a4:f0:0f:64:3c:70", "ligar")

    # próximo ciclo com o OD no meio da histerese: nada muda
    assert _ciclo(db, _previsoes(4.5), publicador)["aerador"] == 0
    assert len(publicador.enviados) == 1


def test_ciclo_sem_confirmacao_do_broker_nao_registra_acionamento(db):
    with db.begin() as conn:
        semear_tanque(conn, TILAPIA)
    assert _ciclo(db, _previsoes(3.5), PublicadorFalso(ok=False))["aerador"] == 0
    with db.connect() as conn:
        assert _acionamentos(conn) == []
        # a previsão continua gravada: só o comando é que não saiu
        assert conn.execute(text("SELECT count(*) FROM previsoes")).scalar_one() == 4


def test_ciclo_sem_aerador_configurado_nao_comanda(db):
    with db.begin() as conn:
        semear_tanque(conn, TILAPIA)
    executar_ciclo(db, InferenciaFixa(_previsoes(3.0)), confianca_min=0.5, agora=AGORA)
    with db.connect() as conn:
        assert _acionamentos(conn) == []


@pytest.mark.parametrize("liga, desliga", [(5.0, 5.0), (5.0, 4.0)])
def test_configuracao_sem_histerese_e_recusada(monkeypatch, liga, desliga):
    from src.config import Settings
    from src.servico.__main__ import _controle_aerador

    monkeypatch.setenv("ML_AERADOR_AUTOMATICO", "true")
    monkeypatch.setenv("MQTT_BROKER_HOST", "localhost")
    monkeypatch.setenv("MQTT_TOPIC_PREFIX", "tcc")
    monkeypatch.setenv("ML_AERADOR_LIGA_OD", str(liga))
    monkeypatch.setenv("ML_AERADOR_DESLIGA_OD", str(desliga))
    with pytest.raises(ValueError, match="histerese"):
        _controle_aerador(Settings())
