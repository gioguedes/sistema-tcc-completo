from pathlib import Path

import pandas as pd
import pytest

from src.dados.carregar import carregar_todos, ler_rdb
from src.dados.limpar import limpar
from src.dados.pontos import Ponto

PONTO = Ponto("111", "lago_x", "Ponto de teste", {"temperatura": "10", "od": "12", "ph": "11"})
CABECALHO = (
    "# Data provided for site 111\n"
    "#    TS_ID       Parameter Description\n"
    "agency_cd\tsite_no\tdatetime\ttz_cd\t10_00010\t10_00010_cd\t12_00300\t12_00300_cd\t11_00400\t11_00400_cd\n"
    "5s\t15s\t20d\t6s\t14n\t10s\t14n\t10s\t14n\t10s\n"
)
# uma linha de cada caso: as duas primeiras atravessam a troca para o horário de verão
LINHAS = [
    "USGS\t111\t2023-03-12 01:45\tCST\t20.0\tA\t7.0\tA\t7.5\tA",
    "USGS\t111\t2023-03-12 03:00\tCDT\t20.1\tA\t7.1\tA\t7.6\tA",
    "USGS\t111\t2023-07-01 12:00\tCDT\t31.0\tA:e\t6.0\tA\t8.0\tA",
    "USGS\t111\t2023-07-01 12:15\tCDT\t25.0\tP\t6.0\tP\t8.0\tP",
    "USGS\t111\t2023-07-01 12:30\tCDT\t\t\t6.0\tA\t8.0\tA",
    "USGS\t111\t2023-01-10 08:00\tCST\t10.0\tA\t11.0\tA\t7.0\tA",
    "USGS\t111\t2023-07-02 12:00\tCDT\t30.0\tA\t8.0\tA\t3.5\tA",
    "USGS\t111\t2023-07-03 12:00\tCDT\t30.0\tA\t20.5\tA\t8.0\tA",
]


def _rdb(pasta: Path, linhas: list[str], cabecalho: str = CABECALHO, nome: str = "2023-01.rdb") -> Path:
    caminho = pasta / nome
    caminho.write_text(cabecalho + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def test_le_rdb_pulando_comentarios_e_linha_de_tipos(tmp_path):
    df = ler_rdb(_rdb(tmp_path, LINHAS), PONTO)
    assert len(df) == 8
    assert list(df.columns) == ["ts", "temperatura", "cd_temperatura", "od", "cd_od", "ph", "cd_ph"]
    assert df["od"].iloc[0] == pytest.approx(7.0)
    assert df["cd_temperatura"].iloc[2] == "A:e"


def test_valor_vazio_vira_nan(tmp_path):
    df = ler_rdb(_rdb(tmp_path, LINHAS), PONTO)
    assert pd.isna(df["temperatura"].iloc[4])
    assert df["cd_temperatura"].iloc[4] == ""


@pytest.mark.parametrize(
    ("local", "fuso", "utc"),
    [
        ("2023-01-01 00:00", "EST", "2023-01-01 05:00"),
        ("2023-07-01 00:00", "EDT", "2023-07-01 04:00"),
        ("2023-01-01 00:00", "CST", "2023-01-01 06:00"),
        ("2023-07-01 00:00", "CDT", "2023-07-01 05:00"),
    ],
)
def test_converte_o_fuso_local_para_utc(tmp_path, local, fuso, utc):
    df = ler_rdb(_rdb(tmp_path, [f"USGS\t111\t{local}\t{fuso}\t20.0\tA\t7.0\tA\t7.5\tA"]), PONTO)
    assert df["ts"].iloc[0] == pd.Timestamp(utc, tz="UTC")


def test_troca_para_horario_de_verao_fica_continua_em_utc(tmp_path):
    df = ler_rdb(_rdb(tmp_path, LINHAS[:2]), PONTO)
    # 01:45 CST e 03:00 CDT são 07:45 e 08:00 UTC: 15 min de diferença, não 1h15
    assert df["ts"].iloc[1] - df["ts"].iloc[0] == pd.Timedelta(minutes=15)


def test_fuso_desconhecido_e_erro(tmp_path):
    with pytest.raises(ValueError, match="fuso desconhecido"):
        ler_rdb(_rdb(tmp_path, ["USGS\t111\t2023-01-01 00:00\tPST\t20.0\tA\t7.0\tA\t7.5\tA"]), PONTO)


def test_usa_a_serie_fixada_quando_o_ponto_tem_varias_profundidades(tmp_path):
    cabecalho = (
        "agency_cd\tsite_no\tdatetime\ttz_cd\t9_00010\t9_00010_cd\t10_00010\t10_00010_cd"
        "\t12_00300\t12_00300_cd\t11_00400\t11_00400_cd\n5s\t15s\t20d\t6s\t14n\t10s\t14n\t10s\t14n\t10s\t14n\t10s\n"
    )
    linha = "USGS\t111\t2023-01-01 00:00\tCST\t18.0\tA\t22.0\tA\t7.0\tA\t7.5\tA"
    df = ler_rdb(_rdb(tmp_path, [linha], cabecalho), PONTO)
    assert df["temperatura"].iloc[0] == pytest.approx(22.0)


def test_coluna_da_serie_fixada_ausente_e_erro(tmp_path):
    outro = Ponto("111", "lago_x", "Ponto de teste", {"temperatura": "99", "od": "12", "ph": "11"})
    with pytest.raises(ValueError, match="99_00010"):
        ler_rdb(_rdb(tmp_path, LINHAS), outro)


def test_carregar_todos_marca_ponto_e_grupo_e_calcula_hash(tmp_path):
    (tmp_path / "111").mkdir()
    _rdb(tmp_path / "111", LINHAS[:2], nome="2023-01.rdb")
    _rdb(tmp_path / "111", LINHAS[2:4], nome="2023-04.rdb")
    df, hashes = carregar_todos(tmp_path, pontos=(PONTO,))
    assert len(df) == 4
    assert list(df.columns[:3]) == ["ponto", "grupo", "ts"]
    assert set(df["grupo"]) == {"lago_x"}
    assert set(hashes) == {"111/2023-01.rdb", "111/2023-04.rdb"}
    assert all(len(h) == 64 for h in hashes.values())


def test_ponto_sem_arquivos_manda_baixar(tmp_path):
    with pytest.raises(FileNotFoundError, match="baixar_usgs"):
        carregar_todos(tmp_path, pontos=(PONTO,))


def test_limpeza_conta_o_que_cada_regra_removeu(tmp_path):
    limpo, removidas = limpar(ler_rdb(_rdb(tmp_path, LINHAS), PONTO))
    # P em tudo e temperatura vazia; 10 °C; pH 3,5; OD 20,5
    assert removidas == {"nao_aprovado": 2, "temperatura": 1, "ph": 1, "od_faixa": 1}
    assert len(limpo) == 3
    assert "cd_od" not in limpo.columns
