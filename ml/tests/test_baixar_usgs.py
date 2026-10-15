from datetime import date

import pytest

from src.dados.baixar_usgs import baixar, montar_url, trimestres
from src.dados.pontos import PONTOS, Ponto

PONTO = Ponto("111", "lago_x", "Ponto de teste", {"temperatura": "10", "od": "12", "ph": "11"})
RDB = b"# comentario\nagency_cd\tsite_no\n5s\t15s\n"


class ObterFalso:
    """Faz o papel do HTTP: guarda as URLs pedidas e devolve sempre o mesmo conteúdo."""

    def __init__(self, conteudo: bytes = RDB) -> None:
        self.conteudo = conteudo
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        return self.conteudo


def test_oito_trimestres_de_2023_e_2024():
    lista = trimestres()
    assert len(lista) == 8
    assert lista[0] == (date(2023, 1, 1), date(2023, 3, 31))
    assert lista[3] == (date(2023, 10, 1), date(2023, 12, 31))
    assert lista[-1] == (date(2024, 10, 1), date(2024, 12, 31))


def test_url_do_servico_iv_em_rdb():
    url = montar_url(PONTO, date(2023, 1, 1), date(2023, 3, 31))
    assert url == (
        "https://waterservices.usgs.gov/nwis/iv/?format=rdb&sites=111"
        "&parameterCd=00010,00300,00400&startDT=2023-01-01&endDT=2023-03-31"
    )


def test_baixa_um_arquivo_por_trimestre(tmp_path):
    obter = ObterFalso()
    gravados = baixar(tmp_path, obter, pontos=(PONTO,))
    assert len(obter.urls) == 8
    assert [g.name for g in gravados][:2] == ["2023-01.rdb", "2023-04.rdb"]
    assert (tmp_path / "111" / "2024-10.rdb").read_bytes() == RDB


def test_pula_o_que_ja_existe(tmp_path):
    existente = tmp_path / "111" / "2023-01.rdb"
    existente.parent.mkdir()
    existente.write_bytes(b"# ja estava aqui\n")
    obter = ObterFalso()
    baixar(tmp_path, obter, pontos=(PONTO,))
    assert len(obter.urls) == 7
    assert "startDT=2023-01-01" not in " ".join(obter.urls)
    assert existente.read_bytes() == b"# ja estava aqui\n"


def test_segunda_execucao_nao_baixa_nada(tmp_path):
    baixar(tmp_path, ObterFalso(), pontos=(PONTO,))
    obter = ObterFalso()
    assert baixar(tmp_path, obter, pontos=(PONTO,)) == []
    assert obter.urls == []


def test_resposta_que_nao_e_rdb_nao_vira_arquivo(tmp_path):
    with pytest.raises(ValueError, match="não é RDB"):
        baixar(tmp_path, ObterFalso(b"<html>Service Unavailable</html>"), pontos=(PONTO,))
    assert list(tmp_path.rglob("*")) == []


def test_constante_tem_os_7_pontos_e_5_corpos_dagua():
    assert len(PONTOS) == 7
    assert len({p.codigo for p in PONTOS}) == 7
    assert {p.grupo for p in PONTOS} == {"lake_houston", "lynchburg", "luce_bayou", "st_lucie", "winona"}
    assert all(set(p.series) == {"temperatura", "od", "ph"} for p in PONTOS)
