from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings
from src.db.models import Dispositivo, Especie, Sensor, Tanque, TipoSensor, Usuario
from src.db.session import criar_engine, criar_session_factory

MAC_DISPOSITIVO_PADRAO = "a4:f0:0f:64:3c:70"

TIPOS_SENSOR_PADRAO = [
    {"grandeza": "ph", "modelo": "SEN0161-V2", "unidade": "pH", "faixa_min": 0, "faixa_max": 14},
    {"grandeza": "temperatura", "modelo": "DS18B20", "unidade": "C", "faixa_min": -10, "faixa_max": 85},
    {"grandeza": "turbidez", "modelo": "SEN0189", "unidade": "NTU", "faixa_min": 0, "faixa_max": 3000},
]


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _obter_ou_criar(session: Session, classe, filtro, **valores):
    instancia = session.scalar(select(classe).where(filtro))
    if instancia is not None:
        return instancia
    instancia = classe(**valores)
    session.add(instancia)
    session.flush()
    return instancia


def semear(session: Session) -> Dispositivo:
    usuario = _obter_ou_criar(
        session,
        Usuario,
        Usuario.email == "operador@piscicultura.local",
        nome="Operador Padrao",
        email="operador@piscicultura.local",
        senha_hash="sem-autenticacao-neste-sub-projeto",
        telefone=None,
        perfil="admin",
        criado_em=_agora(),
    )

    especie = _obter_ou_criar(
        session,
        Especie,
        Especie.nome_cientifico == "Oreochromis niloticus",
        nome_comum="Tilapia do Nilo",
        nome_cientifico="Oreochromis niloticus",
        ph_min=6.5,
        ph_max=8.5,
        temp_min=20.0,
        temp_max=30.0,
        od_min=4.0,
        od_max=8.0,
    )

    tanque = _obter_ou_criar(
        session,
        Tanque,
        Tanque.nome == "Tanque bancada TCC",
        id_usuario=usuario.id,
        id_especie=especie.id,
        nome="Tanque bancada TCC",
        volume_litros=500.0,
        quantidade_peixes=0,
        data_povoamento=None,
        status="ativo",
        criado_em=_agora(),
    )

    dispositivo = _obter_ou_criar(
        session,
        Dispositivo,
        Dispositivo.mac_address == MAC_DISPOSITIVO_PADRAO,
        id_tanque=tanque.id,
        nome="No sensor bancada",
        modelo_esp32="ESP32 DevKitC V4",
        mac_address=MAC_DISPOSITIVO_PADRAO,
        versao_firmware=None,
        ip_local=None,
        status_conexao="offline",
        ultimo_heartbeat=None,
        data_cadastro=_agora(),
    )

    tipos_por_grandeza = {}
    for dados in TIPOS_SENSOR_PADRAO:
        tipo = _obter_ou_criar(session, TipoSensor, TipoSensor.modelo == dados["modelo"], **dados)
        tipos_por_grandeza[dados["grandeza"]] = tipo

    for tipo in tipos_por_grandeza.values():
        ja_existe = session.scalar(
            select(Sensor).where(
                Sensor.id_dispositivo == dispositivo.id,
                Sensor.id_tipo == tipo.id,
            )
        )
        if ja_existe is None:
            session.add(
                Sensor(
                    id_dispositivo=dispositivo.id,
                    id_tipo=tipo.id,
                    id_tanque=tanque.id,
                    data_instalacao=date.today(),
                    status="ativo",
                )
            )

    session.flush()
    return dispositivo


def main() -> None:
    settings = Settings()
    engine = criar_engine(settings)
    session_factory = criar_session_factory(engine)

    with session_factory() as session:
        dispositivo = semear(session)
        session.commit()
        print(f"Dispositivo pronto: mac={dispositivo.mac_address} id={dispositivo.id}")


if __name__ == "__main__":
    main()