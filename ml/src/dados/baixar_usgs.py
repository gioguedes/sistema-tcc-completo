import logging
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from src.config import Settings
from src.dados.pontos import CODIGOS_PARAMETRO, PONTOS, Ponto

logger = logging.getLogger(__name__)

URL_BASE = "https://waterservices.usgs.gov/nwis/iv/"
ANOS = (2023, 2024)
TEMPO_LIMITE_S = 300


def trimestres(anos: tuple[int, ...] = ANOS) -> list[tuple[date, date]]:
    """Primeiro e último dia de cada trimestre: um trimestre por requisição cabe no tempo limite do serviço."""
    saida = []
    for ano in anos:
        for mes in (1, 4, 7, 10):
            proximo = date(ano + 1, 1, 1) if mes == 10 else date(ano, mes + 3, 1)
            saida.append((date(ano, mes, 1), proximo - timedelta(days=1)))
    return saida


def montar_url(ponto: Ponto, inicio: date, fim: date) -> str:
    parametros = {
        "format": "rdb",
        "sites": ponto.codigo,
        "parameterCd": ",".join(CODIGOS_PARAMETRO.values()),
        "startDT": inicio.isoformat(),
        "endDT": fim.isoformat(),
    }
    return f"{URL_BASE}?{urlencode(parametros, safe=',')}"


def _obter_http(url: str) -> bytes:
    # o urlopen segue sozinho o 301 para nwis.waterservices.usgs.gov
    with urlopen(url, timeout=TEMPO_LIMITE_S) as resposta:
        return resposta.read()


def baixar(
    destino: Path, obter: Callable[[str], bytes] = _obter_http, pontos: tuple[Ponto, ...] = PONTOS
) -> list[Path]:
    """Baixa os trimestres que ainda não existem em `destino/<ponto>/<AAAA-MM>.rdb`; devolve os gravados agora."""
    gravados = []
    for ponto in pontos:
        for inicio, fim in trimestres():
            arquivo = destino / ponto.codigo / f"{inicio:%Y-%m}.rdb"
            if arquivo.exists():
                continue
            conteudo = obter(montar_url(ponto, inicio, fim))
            if not conteudo.startswith(b"#"):
                raise ValueError(
                    f"resposta do USGS não é RDB ({ponto.codigo} {inicio:%Y-%m}): {conteudo[:80]!r}"
                )
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            # grava num temporário e renomeia: um download interrompido não deixa
            # um .rdb pela metade que a próxima execução pularia
            temporario = arquivo.with_suffix(".tmp")
            temporario.write_bytes(conteudo)
            temporario.replace(arquivo)
            gravados.append(arquivo)
            logger.info("%s gravado (%d bytes)", arquivo, len(conteudo))
    return gravados


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    destino = Settings().ml_datasets_dir / "usgs"
    gravados = baixar(destino)
    logger.info("%d arquivos novos em %s", len(gravados), destino)


if __name__ == "__main__":
    main()
