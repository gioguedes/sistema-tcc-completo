"""Dados de teste no formato que a ingestao e o servico de ML gravam."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from src.db.models import Leitura, Previsao, Sensor, Tanque, TipoSensor

MINUTO = timedelta(minutes=1)
SENHA = "senha-de-teste"
UNIDADES = {"ph": "pH", "temperatura": "C", "turbidez": "NTU"}


class PublicadorFalso:
    """No lugar do broker MQTT: guarda os comandos e pode simular o broker fora do ar."""

    def __init__(self) -> None:
        self.publicados: list[dict] = []
        self.disponivel = True

    def iniciar(self) -> None:
        pass

    def parar(self) -> None:
        pass

    def publicar_aerador(self, mac: str, acao: str, id_acionamento: int, ts: int) -> bool:
        if not self.disponivel:
            return False
        self.publicados.append({"mac": mac, "acao": acao, "id": id_acionamento, "ts": ts})
        return True


def agora() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def sensores(db_session, tanque: Tanque) -> dict[str, Sensor]:
    linhas = db_session.execute(
        select(TipoSensor.grandeza, Sensor)
        .join(Sensor, Sensor.id_tipo == TipoSensor.id)
        .where(Sensor.id_tanque == tanque.id)
    ).all()
    return {grandeza: sensor for grandeza, sensor in linhas}


def gravar_leituras(db_session, tanque: Tanque, ts: datetime, **valores: float) -> None:
    """Uma mensagem do no: `gravar_leituras(s, t, ts, ph=7.1, temperatura=26.0)`."""
    por_grandeza = sensores(db_session, tanque)
    for grandeza, valor in valores.items():
        db_session.add(
            Leitura(id_sensor=por_grandeza[grandeza].id, valor=valor, unidade=UNIDADES[grandeza], ts=ts)
        )
    db_session.flush()


def gravar_ciclo(
    db_session,
    tanque: Tanque,
    ts: datetime,
    od: float = 5.6,
    nivel_od: str = "otimo",
    confianca_od: float = 0.8,
    niveis: tuple[str, str, str] = ("otimo", "atencao", "critico"),
) -> None:
    """As 4 linhas de um ciclo do servico de ML: h = 0 (OD agora) e h = 1..3, com o mesmo ts_previsao."""
    db_session.add(
        Previsao(
            id_tanque=tanque.id, parametro_critico="od", valor_previsto=od, nivel_risco=nivel_od,
            horizonte_h=0, confianca=confianca_od, ts_previsao=ts,
        )
    )
    for h, nivel in enumerate(niveis, start=1):
        db_session.add(
            Previsao(
                id_tanque=tanque.id, parametro_critico="ph", valor_previsto=7.0 + h / 10, nivel_risco=nivel,
                horizonte_h=h, confianca=0.9, ts_previsao=ts,
            )
        )
    db_session.flush()
