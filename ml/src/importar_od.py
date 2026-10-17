import argparse
import logging
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import Connection, create_engine, text

from src.config import Settings

logger = logging.getLogger(__name__)

MODELO_REFERENCIA = "Referencia manual"

SQL_TIPO = text(
    """
    INSERT INTO tipos_sensor (grandeza, modelo, unidade, faixa_min, faixa_max)
    VALUES ('od', :modelo, 'mg/L', 0, 20)
    ON CONFLICT (modelo) DO UPDATE SET modelo = EXCLUDED.modelo
    RETURNING id
    """
)
SQL_SENSOR_EXISTENTE = text("SELECT id FROM sensores WHERE id_tanque = :t AND id_tipo = :tipo ORDER BY id LIMIT 1")
SQL_DISPOSITIVO = text("SELECT id FROM dispositivos WHERE id_tanque = :t ORDER BY id LIMIT 1")
SQL_NOVO_SENSOR = text(
    """
    INSERT INTO sensores (id_dispositivo, id_tipo, id_tanque, data_instalacao, status)
    VALUES (:d, :tipo, :t, :hoje, 'ativo')
    RETURNING id
    """
)
SQL_LEITURA = text(
    """
    INSERT INTO leituras (id_sensor, valor, unidade, ts)
    VALUES (:s, :v, 'mg/L', :ts)
    ON CONFLICT (id_sensor, ts) DO NOTHING
    RETURNING id
    """
)


def ler_csv(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(caminho)
    if list(df.columns) != ["ts", "od_mg_l"]:
        raise ValueError(f"cabeçalho esperado: ts,od_mg_l (veio {','.join(df.columns)})")
    texto = df["ts"].astype(str).str.strip()
    # sem fuso explícito não dá para saber se a hora anotada é local ou UTC
    tem_fuso = texto.str.contains(r"(?:Z|[+-]\d{2}:\d{2})$", regex=True)
    ts = pd.to_datetime(texto, format="ISO8601", utc=True, errors="coerce")
    if not tem_fuso.all() or ts.isna().any():
        raise ValueError("ts precisa estar em ISO 8601 com fuso, por exemplo 2026-10-01T08:00:00-03:00")
    od = pd.to_numeric(df["od_mg_l"], errors="coerce")
    if od.isna().any() or not od.between(0, 20).all():
        raise ValueError("od_mg_l precisa ser número entre 0 e 20")
    return pd.DataFrame({"ts": ts, "od_mg_l": od})


def _sensor_referencia(conn: Connection, id_tanque: int) -> int:
    id_tipo = conn.execute(SQL_TIPO, {"modelo": MODELO_REFERENCIA}).scalar_one()
    existente = conn.execute(SQL_SENSOR_EXISTENTE, {"t": id_tanque, "tipo": id_tipo}).scalar()
    if existente is not None:
        return existente
    # sensores.id_dispositivo é NOT NULL: o sensor manual fica pendurado no nó do tanque
    id_dispositivo = conn.execute(SQL_DISPOSITIVO, {"t": id_tanque}).scalar()
    if id_dispositivo is None:
        raise ValueError(f"tanque {id_tanque} não tem dispositivo cadastrado")
    return conn.execute(
        SQL_NOVO_SENSOR, {"d": id_dispositivo, "tipo": id_tipo, "t": id_tanque, "hoje": date.today()}
    ).scalar_one()


def importar(conn: Connection, medicoes: pd.DataFrame, id_tanque: int) -> int:
    """Grava as medições como leituras do sensor de referência; devolve quantas eram novas."""
    id_sensor = _sensor_referencia(conn, id_tanque)
    novas = 0
    for linha in medicoes.itertuples():
        inserida = conn.execute(SQL_LEITURA, {"s": id_sensor, "v": float(linha.od_mg_l), "ts": linha.ts}).first()
        if inserida is not None:
            novas += 1
    return novas


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Importa medições manuais de OD (CSV ts,od_mg_l)")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--tanque", type=int, required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    medicoes = ler_csv(args.csv)
    engine = create_engine(Settings().database_url)
    with engine.begin() as conn:
        novas = importar(conn, medicoes, args.tanque)
    logger.info("%d medições lidas, %d novas gravadas no tanque %d", len(medicoes), novas, args.tanque)


if __name__ == "__main__":
    main()
