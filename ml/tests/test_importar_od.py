from pathlib import Path

import pytest
from sqlalchemy import text

from src.importar_od import importar, ler_csv
from tests.banco import semear_tanque

CSV_OK = """ts,od_mg_l
2026-10-01T08:00:00-03:00,6.4
2026-10-01T14:00:00-03:00,7.1
"""


def _csv(tmp_path: Path, conteudo: str) -> Path:
    caminho = tmp_path / "od.csv"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_ler_csv_aceita_fusos_diferentes_no_mesmo_arquivo(tmp_path):
    conteudo = "ts,od_mg_l\n2026-10-01T08:00:00-03:00,6.4\n2026-10-01T12:00:00Z,6.0\n"
    medicoes = ler_csv(_csv(tmp_path, conteudo))
    assert [str(t) for t in medicoes["ts"]] == ["2026-10-01 11:00:00+00:00", "2026-10-01 12:00:00+00:00"]


def test_ler_csv_converte_para_utc(tmp_path):
    medicoes = ler_csv(_csv(tmp_path, CSV_OK))
    assert str(medicoes["ts"].iloc[0]) == "2026-10-01 11:00:00+00:00"
    assert list(medicoes["od_mg_l"]) == [6.4, 7.1]


@pytest.mark.parametrize(
    "conteudo",
    [
        "ts,od_mg_l\n2026-10-01T08:00:00,6.4\n",
        "ts,od_mg_l\nontem,6.4\n",
        "ts,od_mg_l\n2026-10-01T08:00:00-03:00,abc\n",
        "ts,od_mg_l\n2026-10-01T08:00:00-03:00,25\n",
        "data,od\n2026-10-01T08:00:00-03:00,6.4\n",
    ],
    ids=["sem-fuso", "data-invalida", "od-texto", "od-fora-da-faixa", "cabecalho-errado"],
)
def test_ler_csv_rejeita_entrada_invalida(tmp_path, conteudo):
    with pytest.raises(ValueError):
        ler_csv(_csv(tmp_path, conteudo))


def test_importar_cria_sensor_de_referencia_e_nao_duplica(db, tmp_path):
    medicoes = ler_csv(_csv(tmp_path, CSV_OK))
    with db.begin() as conn:
        ids = semear_tanque(conn)
        assert importar(conn, medicoes, ids["id_tanque"]) == 2
        assert importar(conn, medicoes, ids["id_tanque"]) == 0
        grandezas = conn.execute(
            text(
                "SELECT tp.grandeza, count(*) FROM leituras l "
                "JOIN sensores s ON s.id = l.id_sensor JOIN tipos_sensor tp ON tp.id = s.id_tipo "
                "WHERE s.id_tanque = :t GROUP BY tp.grandeza"
            ),
            {"t": ids["id_tanque"]},
        ).all()
    assert grandezas == [("od", 2)]


def test_tanque_sem_dispositivo_da_erro_claro(db, tmp_path):
    medicoes = ler_csv(_csv(tmp_path, CSV_OK))
    with db.begin() as conn:
        ids = semear_tanque(conn)
        conn.execute(text("DELETE FROM dispositivos WHERE id = :d"), {"d": ids["id_dispositivo"]})
        with pytest.raises(ValueError, match="dispositivo"):
            importar(conn, medicoes, ids["id_tanque"])
