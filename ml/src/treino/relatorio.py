import json
from pathlib import Path

META_MAE_OD = 0.8
META_ACURACIA_RISCO = 0.80
MODELOS_OD = ("xgboost", "random_forest", "mediana")
MODELOS_RISCO = ("xgboost", "random_forest", "persistencia")


def veredito_h1(metricas_od: dict) -> bool:
    return metricas_od["xgboost"]["mae"] <= META_MAE_OD


def veredito_h2_tc1(metricas_horizonte: dict) -> bool:
    """Critério do TC1 (RNF03, CT04): acurácia da previsão de risco >= 80%."""
    return metricas_horizonte["xgboost"]["acuracia"] >= META_ACURACIA_RISCO


def veredito_h2(metricas_horizonte: dict) -> bool:
    """Critério da spec: o do TC1 e, além disso, recall de crítico acima do da persistência."""
    xgb = metricas_horizonte["xgboost"]
    return (
        xgb["acuracia"] >= META_ACURACIA_RISCO
        and xgb["recall_critico"] > metricas_horizonte["persistencia"]["recall_critico"]
    )


def _sim_nao(valor: bool) -> str:
    return "**ATINGIDA**" if valor else "**NÃO atingida**"


def _tabela_od(por_modelo: dict) -> list[str]:
    linhas = ["| Modelo | MAE (mg/L) | RMSE | R² | Acurácia de faixa |", "|---|---|---|---|---|"]
    for nome in MODELOS_OD:
        m = por_modelo[nome]
        linhas.append(f"| {nome} | {m['mae']:.3f} | {m['rmse']:.3f} | {m['r2']:.3f} | {m['acuracia_faixa']:.1%} |")
    return linhas


def _tabela_od_por_grupo(validacao: dict) -> list[str]:
    linhas = ["| Corpo d'água fora | MAE XGBoost | MAE Random Forest | MAE mediana |", "|---|---|---|---|"]
    for grupo, m in [*validacao["por_grupo"].items(), ("**média**", validacao["media"])]:
        linhas.append(f"| {grupo} | " + " | ".join(f"{m[n]['mae']:.3f}" for n in MODELOS_OD) + " |")
    return linhas


def _tabela_risco(por_modelo: dict) -> list[str]:
    linhas = [
        f"Distribuição ótimo/atenção/crítico: {por_modelo['distribuicao_teste']}",
        "",
        "| Modelo | Acurácia | F1 macro | Recall crítico | Matriz de confusão |",
        "|---|---|---|---|---|",
    ]
    for nome in MODELOS_RISCO:
        m = por_modelo[nome]
        linhas.append(
            f"| {nome} | {m['acuracia']:.1%} | {m['f1_macro']:.3f} | {m['recall_critico']:.1%} | {m['matriz_confusao']} |"
        )
    return linhas


def _tabela_risco_por_grupo(validacao: dict, h: int) -> list[str]:
    linhas = [
        "| Corpo d'água fora | Acurácia XGBoost | Recall crítico XGBoost | Acurácia RF | Acurácia persistência | Recall crítico persistência |",
        "|---|---|---|---|---|---|",
    ]
    for grupo, por_h in [*validacao["por_grupo"].items(), ("**média**", validacao["media"])]:
        m = por_h[h]
        linhas.append(
            f"| {grupo} | {m['xgboost']['acuracia']:.1%} | {m['xgboost']['recall_critico']:.1%} | "
            f"{m['random_forest']['acuracia']:.1%} | {m['persistencia']['acuracia']:.1%} | "
            f"{m['persistencia']['recall_critico']:.1%} |"
        )
    return linhas


def _secao_risco(risco: dict) -> list[str]:
    linhas = []
    for h, por_modelo in risco["teste"].items():
        linhas += [
            "", f"### Horizonte {h} h", "", "Teste final:", "", *_tabela_risco(por_modelo), "",
            f"H2 neste horizonte, critério do TC1 (acurácia ≥ 80%): {_sim_nao(veredito_h2_tc1(por_modelo))} | "
            f"critério da spec (também ganhar da persistência no recall de crítico): {_sim_nao(veredito_h2(por_modelo))}",
            "",
            "Validação cruzada por corpo d'água (treino):", "", *_tabela_risco_por_grupo(risco["validacao_cruzada"], h),
            "", "Split temporal (2023 → 2024, corpos de treino):", "", *_tabela_risco(risco["temporal"][h]),
        ]
    return linhas


def gerar_relatorio(dados: dict, pasta: Path) -> Path:
    """Grava relatorio_treino.json (tudo) e relatorio_treino.md (legível); devolve o .md."""
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "relatorio_treino.json").write_text(
        json.dumps(dados, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    od, niveis = dados["od"], dados["distribuicao_niveis"]
    total_niveis = sum(niveis)
    linhas = [
        "# Relatório de treino: estimador de OD e classificador de risco",
        "",
        f"Gerado em: {dados['criado_em']}",
        "",
        "## Dados (USGS, só leituras aprovadas, blocos de 15 min)",
        "",
        "| Corpo d'água | Pontos | Blocos válidos |",
        "|---|---|---|",
        *[
            f"| {g} | {', '.join(p for p, gp in dados['pontos'].items() if gp == g)} | {n} |"
            for g, n in dados["linhas_por_grupo"].items()
        ],
        "",
        f"Teste final (CT04): {dados['grupos_teste']} ({dados['fracao_teste']:.1%} dos blocos). "
        f"Treino: {dados['grupos_treino']}.",
        "",
        f"Níveis pela faixa da tilápia em todos os blocos: ótimo {niveis[0] / total_niveis:.1%}, "
        f"atenção {niveis[1] / total_niveis:.1%}, crítico {niveis[2] / total_niveis:.1%}.",
        "",
        "## Limpeza (linhas removidas por regra)",
        "",
        *[f"- {regra}: {n}" for regra, n in dados["limpeza"].items()],
        f"- linhas brutas: {dados['linhas_brutas']} | após limpeza: {dados['linhas_limpas']}",
        "",
        "## Estimador de OD (H1: MAE ≤ 0,8 mg/L no teste final)",
        "",
        "Teste final:",
        "",
        *_tabela_od(od["teste"]),
        "",
        f"H1: {_sim_nao(veredito_h1(od['teste']))}",
        "",
        "Validação cruzada por corpo d'água (treino):",
        "",
        *_tabela_od_por_grupo(od["validacao_cruzada"]),
        "",
        "Split temporal (2023 → 2024, corpos de treino):",
        "",
        *_tabela_od(od["temporal"]),
        "",
        "## Classificador de risco (H2: acurácia ≥ 80% pelo TC1; a spec exige também recall de crítico acima da persistência)",
        *_secao_risco(dados["risco"]),
        "",
        "## Datasets (SHA-256)",
        "",
        *[f"- `{nome}`: `{h}`" for nome, h in dados["hashes_datasets"].items()],
        "",
    ]
    caminho_md = pasta / "relatorio_treino.md"
    caminho_md.write_text("\n".join(linhas), encoding="utf-8")
    return caminho_md
