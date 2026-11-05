"""Confere os .stl gerados: cabem na A1 mini e apoiam na mesa (z minimo = 0)."""
import pathlib
import sys

MESA = 180.0
STL = pathlib.Path(__file__).parent / "stl"


def caixa_limite(caminho):
    minimo = [float("inf")] * 3
    maximo = [float("-inf")] * 3
    for linha in caminho.read_text().splitlines():
        partes = linha.split()
        if partes[:1] == ["vertex"]:
            for i, v in enumerate(map(float, partes[1:4])):
                minimo[i] = min(minimo[i], v)
                maximo[i] = max(maximo[i], v)
    return minimo, maximo


falhas = 0
arquivos = sorted(STL.glob("*.stl"))
if not arquivos:
    sys.exit("nenhum .stl em stl/ - rode gerar.ps1 antes")
for arq in arquivos:
    minimo, maximo = caixa_limite(arq)
    tam = [b - a for a, b in zip(minimo, maximo)]
    problemas = []
    if any(t > MESA for t in tam):
        problemas.append("nao cabe na mesa")
    if abs(minimo[2]) > 0.01:
        problemas.append(f"z minimo = {minimo[2]:.2f}, deveria ser 0")
    falhas += bool(problemas)
    print(f"{'FALHA' if problemas else 'ok   '} {arq.stem:18} "
          f"{tam[0]:6.1f} x {tam[1]:6.1f} x {tam[2]:6.1f} mm  {'; '.join(problemas)}")
sys.exit(1 if falhas else 0)
