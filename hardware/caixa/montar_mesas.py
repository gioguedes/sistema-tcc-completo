"""Junta os .stl de stl/ em um .stl por mesa de impressao (Bambu Lab A1 mini, 180 x 180 mm).

As pecas de cada mesa ja saem na posicao certa, dentro de um unico arquivo. Rode depois do gerar.ps1.
"""
import pathlib
import struct
import sys

import numpy as np

MESA = 180.0
BORDA = 5.0  # largura do brim reservada em volta das pecas marcadas
AQUI = pathlib.Path(__file__).parent
STL = AQUI / "stl"
SAIDA = AQUI / "mesas"

# (arquivo .stl, canto minimo [x, y] na mesa, usa borda)
MESAS = {
    "0-provas-opcional": [
        ("prova_suporte", [10, 10], False),
        ("prova_tampa", [10, 40], False),
        ("prova_base", [75, 40], False),
        ("prova_gancho", [115, 40], False),
        ("parafuso", [75, 90], False),
    ],
    "1-base-e-parafusos": [
        ("base", [2.1, 51], False),
        ("parafuso", [10, 16], False),
        ("parafuso", [50, 16], False),
        ("parafuso", [90, 16], False),
        ("parafuso", [130, 16], False),
    ],
    "2-gancho-e-suporte": [
        ("suporte_braco", [4, 10], False),
        ("gancho", [93, 28], True),
        ("suporte_presilha", [130, 12], True),
    ],
    "3-tampa": [
        ("tampa", [5.1, 29.6], False),
    ],
}


def ler_stl(caminho):
    v = [l.split()[1:4] for l in caminho.read_text().splitlines() if l.lstrip().startswith("vertex")]
    return np.array(v, dtype=np.float64).reshape(-1, 3, 3)


def escrever_stl(caminho, tri):
    normais = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normais /= np.maximum(np.linalg.norm(normais, axis=1, keepdims=True), 1e-12)
    registros = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    registros["n"], registros["v"] = normais, tri
    with open(caminho, "wb") as f:
        f.write(caminho.stem.encode().ljust(80, b" "))
        f.write(struct.pack("<I", len(tri)))
        f.write(registros.tobytes())


def sobrepoe(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


SAIDA.mkdir(exist_ok=True)
falhas = 0
for mesa, pecas in MESAS.items():
    malhas, caixas = [], []
    for nome, canto, borda in pecas:
        tri = ler_stl(STL / f"{nome}.stl")
        minimo = tri.reshape(-1, 3).min(0)
        tri = tri + [canto[0] - minimo[0], canto[1] - minimo[1], -minimo[2]]
        mn, mx = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
        folga = BORDA if borda else 0
        caixas.append((nome, [mn[0] - folga, mn[1] - folga, mx[0] + folga, mx[1] + folga]))
        malhas.append(tri)
    problemas = [f"{n} sai da mesa" for n, c in caixas if c[0] < 0 or c[1] < 0 or c[2] > MESA or c[3] > MESA]
    problemas += [f"{a} encosta em {b}" for i, (a, ca) in enumerate(caixas) for b, cb in caixas[i + 1:]
                  if sobrepoe(ca, cb)]
    escrever_stl(SAIDA / f"{mesa}.stl", np.concatenate(malhas))
    falhas += bool(problemas)
    print(f"{'FALHA' if problemas else 'ok   '} {mesa:22} {len(pecas)} pecas  {'; '.join(problemas)}")
sys.exit(1 if falhas else 0)
