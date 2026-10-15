from dataclasses import dataclass


@dataclass(frozen=True)
class Ponto:
    codigo: str
    grupo: str
    descricao: str
    # TS_ID da série de cada grandeza no RDB (o número antes de _00010 etc.)
    series: dict[str, str]


# grupo = corpo d'água: a unidade de separação entre treino e teste
PONTOS = (
    Ponto("295826095082200", "lake_houston", "Lk Houston S Union Pacific RR Bridge, TX",
          {"temperatura": "142509", "od": "142512", "ph": "142511"}),
    # o ponto tem sondas a 1, 6, 12 e 14 ft; só a de 12 ft cobre 2023 e 2024 inteiros
    Ponto("295554095093402", "lake_houston", "Lk Houston at Jack's Ditch (Site 2), TX",
          {"temperatura": "142494", "od": "142498", "ph": "142496"}),
    Ponto("300032095080501", "lake_houston", "Lk Houston at FM 1960 nr Huffman, TX",
          {"temperatura": "234846", "od": "234851", "ph": "234849"}),
    Ponto("294643095035200", "lynchburg", "Lynchburg Res nr CWA Canal Inflow, TX",
          {"temperatura": "163507", "od": "163511", "ph": "163509"}),
    Ponto("08066850", "luce_bayou", "Luce Bayou ITP Canal at Capers Ridge, TX",
          {"temperatura": "309129", "od": "309131", "ph": "309134"}),
    Ponto("02276998", "st_lucie", "St Lucie Canal abv S-80 nr Stuart, FL",
          {"temperatura": "233564", "od": "233566", "ph": "237032"}),
    Ponto("073625897", "winona", "Lake Winona Raw Water Intake, AR",
          {"temperatura": "4969", "od": "4971", "ph": "4972"}),
)

CODIGOS_PARAMETRO = {"temperatura": "00010", "od": "00300", "ph": "00400"}
