from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from src.faixas import TILAPIA, FaixaEspecie


def semear_tanque(conn, faixa: FaixaEspecie = TILAPIA, mac: str = "a4:f0:0f:64:3c:70", status: str = "ativo") -> dict:
    """Usuário, espécie, tanque, dispositivo e sensores de pH e temperatura; devolve os ids."""
    agora = datetime.now(timezone.utc)
    id_usuario = conn.execute(
        text(
            "INSERT INTO usuarios (nome, email, senha_hash, perfil, criado_em) "
            "VALUES ('Teste', :email, 'x', 'admin', :agora) RETURNING id"
        ),
        {"email": f"{mac}@teste", "agora": agora},
    ).scalar_one()
    id_especie = conn.execute(
        text(
            "INSERT INTO especies (nome_comum, nome_cientifico, ph_min, ph_max, temp_min, temp_max, od_min, od_max) "
            "VALUES ('Especie', :nome, :ph_min, :ph_max, :temp_min, :temp_max, :od_min, :od_max) RETURNING id"
        ),
        {"nome": f"especie {mac}", **asdict(faixa)},
    ).scalar_one()
    id_tanque = conn.execute(
        text(
            "INSERT INTO tanques (id_usuario, id_especie, nome, volume_litros, quantidade_peixes, status, criado_em) "
            "VALUES (:u, :e, 'Tanque', 500, 0, :status, :agora) RETURNING id"
        ),
        {"u": id_usuario, "e": id_especie, "status": status, "agora": agora},
    ).scalar_one()
    id_dispositivo = conn.execute(
        text(
            "INSERT INTO dispositivos (id_tanque, nome, modelo_esp32, mac_address, status_conexao, data_cadastro) "
            "VALUES (:t, 'No', 'DevKitC', :mac, 'offline', :agora) RETURNING id"
        ),
        {"t": id_tanque, "mac": mac, "agora": agora},
    ).scalar_one()

    sensores = {}
    for grandeza, unidade in (("ph", "pH"), ("temperatura", "C")):
        id_tipo = conn.execute(
            text(
                "INSERT INTO tipos_sensor (grandeza, modelo, unidade, faixa_min, faixa_max) "
                "VALUES (:g, :modelo, :u, 0, 100) "
                "ON CONFLICT (modelo) DO UPDATE SET grandeza = EXCLUDED.grandeza RETURNING id"
            ),
            {"g": grandeza, "modelo": f"modelo-{grandeza}", "u": unidade},
        ).scalar_one()
        sensores[grandeza] = conn.execute(
            text(
                "INSERT INTO sensores (id_dispositivo, id_tipo, id_tanque, status) "
                "VALUES (:d, :tipo, :t, 'ativo') RETURNING id"
            ),
            {"d": id_dispositivo, "tipo": id_tipo, "t": id_tanque},
        ).scalar_one()
    return {"id_tanque": id_tanque, "id_dispositivo": id_dispositivo, "sensores": sensores}


def inserir_leituras(conn, id_sensor: int, inicio: datetime, valores: list[float]) -> None:
    conn.execute(
        text("INSERT INTO leituras (id_sensor, valor, unidade, ts) VALUES (:s, :v, 'x', :ts)"),
        [
            {"s": id_sensor, "v": v, "ts": inicio + timedelta(minutes=i)}
            for i, v in enumerate(valores)
        ],
    )
