"""Alertas de qualidade da água (RF06, UC04): avisa o N8N por webhook quando o estado do tanque muda.

Roda fora do ciclo de ML, que no modo normal só passa a cada 5 min, e olha as leituras, e não a mediana
do bloco. A condição crítica de pH ou temperatura só vale com duas leituras seguidas do mesmo lado da
faixa: o alerta sai depois da segunda, ou seja, um intervalo de leitura do nó mais um ciclo deste serviço
depois da primeira leitura crítica. O caso só encerra depois de cinco leituras seguidas sem nenhuma crítica.
"""

import argparse
import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import Connection, Engine, create_engine, text

from src.config import Settings
from src.faixas import CRITICO, NOMES_NIVEL, TILAPIA, FaixaEspecie, nivel
from src.servico.janela import tanques_ativos

logger = logging.getLogger(__name__)

TEMPO_LIMITE_S = 5.0
LEITURA_RECENTE = timedelta(minutes=10)
PREVISAO_RECENTE = timedelta(minutes=15)
LEITURAS_PARA_ABRIR = 2
LEITURAS_PARA_ENCERRAR = 5

# medido vem antes de estimado: o OD é uma estimativa e não deve esconder um pH fora da faixa
GRANDEZAS_MEDIDAS = {"ph": ("ph_baixo", "ph_alto"), "temperatura": ("temperatura_baixa", "temperatura_alta")}
GRANDEZA_DO_CASO = {caso: g for g, casos in GRANDEZAS_MEDIDAS.items() for caso in casos} | {"od_baixo": "od"}
CASOS = ("normal", *GRANDEZA_DO_CASO)

UNIDADES = {"ph": "pH", "temperatura": "°C", "od": "mg/L"}
RECOMENDACOES = {
    "normal": "Nenhuma ação necessária. Mantenha o acompanhamento.",
    "ph_alto": "Confira o sensor e a água. Se confirmar, faça uma troca parcial de água, sem correções bruscas.",
    "ph_baixo": "Confira o sensor e a água. Se confirmar, faça uma troca parcial de água, sem correções bruscas.",
    "temperatura_alta": "Confira o sensor. Se confirmar, sombreie o tanque e reforce a aeração.",
    "temperatura_baixa": "Confira o sensor. Se confirmar, proteja o tanque do frio e reduza a alimentação.",
    "od_baixo": "O OD é estimado: confirme com medição direta, se possível, e reforce a aeração.",
}


def _br(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _caso_da_leitura(valor: float, grandeza: str, faixa: FaixaEspecie) -> str | None:
    if nivel(valor, grandeza, faixa) != CRITICO:
        return None
    baixo, alto = GRANDEZAS_MEDIDAS[grandeza]
    return baixo if valor < faixa.limites(grandeza)[0] else alto


def classificar(
    leituras: dict[str, list[float]],
    od: tuple[float, float] | None,
    faixa: FaixaEspecie,
    confianca_min: float,
    anterior: str | None,
) -> str | None:
    """Caso atual do tanque; None enquanto não dá para dizer (sem leitura recente, ou só uma leitura crítica antes de qualquer envio).

    `leituras` vem da mais nova para a mais antiga; `od` é (valor, confiança); `anterior` é o último caso enviado.
    """
    if not any(leituras.get(g) for g in GRANDEZAS_MEDIDAS):
        return None
    recentes = {
        g: [_caso_da_leitura(v, g, faixa) for v in leituras.get(g, [])[:LEITURAS_PARA_ENCERRAR]]
        for g in GRANDEZAS_MEDIDAS
    }
    for casos in recentes.values():
        confirmacao = casos[:LEITURAS_PARA_ABRIR]
        if len(confirmacao) == LEITURAS_PARA_ABRIR and casos[0] is not None and len(set(confirmacao)) == 1:
            return casos[0]
    # o OD já vem da mediana de um bloco de leituras: não precisa de segunda confirmação
    if od is not None and od[1] >= confianca_min and nivel(od[0], "od", faixa) == CRITICO:
        return "od_baixo"
    # uma leitura crítica isolada não abre o alerta: com o pH perto do limite, o ruído do eletrodo cruza a
    # borda sozinho. Fica o caso anterior até a leitura seguinte confirmar ou desmentir
    if any(casos and casos[0] is not None for casos in recentes.values()):
        return anterior
    # e o caso só encerra sem nenhuma leitura crítica entre as últimas LEITURAS_PARA_ENCERRAR: com a água na
    # borda do limite, sair e voltar em poucos minutos viraria um par de mensagens a cada oscilação
    if any(recentes.get(GRANDEZA_DO_CASO.get(anterior), [])):
        return anterior
    return "normal"


def _mensagem(caso: str, tanque: str, valores: dict[str, float | None], faixa: FaixaEspecie) -> str:
    ph, temperatura = valores.get("ph"), valores.get("temperatura")
    if caso == "normal":
        partes = []
        if ph is not None:
            partes.append(f"pH {_br(ph)}")
        if temperatura is not None:
            partes.append(f"temperatura {_br(temperatura, 1)} °C")
        return f"{tanque}: água fora da condição crítica ({' e '.join(partes)})."
    grandeza = GRANDEZA_DO_CASO[caso]
    minimo, maximo = faixa.limites(grandeza)
    if grandeza == "ph":
        limite = f"abaixo do limite de {_br(minimo, 1)}" if caso == "ph_baixo" else f"acima do limite de {_br(maximo, 1)}"
        return f"{tanque}: risco crítico. pH {_br(ph)}, {limite}."
    if grandeza == "temperatura":
        limite = f"abaixo de {_br(minimo, 1)} °C" if caso == "temperatura_baixa" else f"acima de {_br(maximo, 1)} °C"
        return f"{tanque}: risco crítico. Temperatura {_br(temperatura, 1)} °C, {limite}."
    return f"{tanque}: risco crítico. OD estimado {_br(valores['od'], 1)} mg/L, abaixo de {_br(minimo, 1)} mg/L."


def montar_alerta(
    caso: str,
    id_alerta: int | None,
    id_tanque: int,
    tanque: str,
    telefone: str | None,
    valores: dict[str, float | None],
    confianca_od: float | None,
    risco_previsto: dict[str, str],
    faixa: FaixaEspecie,
    ts_leitura: datetime | None,
    agora: datetime,
) -> dict:
    grandeza = GRANDEZA_DO_CASO.get(caso)
    if grandeza is None:
        medidos = [nivel(valores[g], g, faixa) for g in GRANDEZAS_MEDIDAS if valores.get(g) is not None]
        nivel_risco = NOMES_NIVEL[max(medidos)]
    else:
        nivel_risco = NOMES_NIVEL[CRITICO]
    minimo, maximo = faixa.limites(grandeza) if grandeza else (None, None)
    return {
        "evento": "alerta_qualidade_agua",
        "simulado": False,
        "id_alerta": id_alerta,
        "caso": caso,
        "nivel_risco": nivel_risco,
        "parametro": grandeza,
        "valor": valores.get(grandeza) if grandeza else None,
        "unidade": UNIDADES.get(grandeza),
        "faixa_min": minimo,
        "faixa_max": maximo,
        "id_tanque": id_tanque,
        "tanque": tanque,
        "telefone": telefone,
        "mensagem": _mensagem(caso, tanque, valores, faixa),
        "recomendacao": RECOMENDACOES[caso],
        "ph": valores.get("ph"),
        "temperatura": valores.get("temperatura"),
        "od_estimado": valores.get("od"),
        "od_confianca": confianca_od,
        "risco_previsto": risco_previsto,
        "ts_leitura": ts_leitura.isoformat() if ts_leitura else None,
        "ts_disparo": agora.isoformat(),
    }


class Destino(Protocol):
    def enviar(self, alerta: dict) -> bool: ...


class Webhook:
    def __init__(self, url: str, token: str = "") -> None:
        self._url = url
        self._token = token

    def enviar(self, alerta: dict) -> bool:
        cabecalhos = {"Content-Type": "application/json"}
        if self._token:
            cabecalhos["Authorization"] = f"Bearer {self._token}"
        pedido = urllib.request.Request(
            self._url, data=json.dumps(alerta, ensure_ascii=False).encode("utf-8"), headers=cabecalhos, method="POST"
        )
        try:
            with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE_S) as resposta:
                return 200 <= resposta.status < 300
        except (OSError, ValueError) as erro:
            # sem a URL no log: quem tem a URL de um webhook consegue disparar o workflow.
            # O código HTTP entra porque diz o que acertar no N8N (404: workflow inativo ou caminho errado)
            detalhe = f"HTTP {erro.code}" if isinstance(erro, urllib.error.HTTPError) else type(erro).__name__
            logger.warning("webhook de alertas falhou: %s", detalhe)
            return False


SQL_WEBHOOK = text("SELECT valor FROM configuracoes WHERE chave = 'alertas_webhook_url'")
SQL_LEITURAS = text(
    """
    SELECT grandeza, ts, valor FROM (
        SELECT tp.grandeza, l.ts, l.valor,
               row_number() OVER (PARTITION BY tp.grandeza ORDER BY l.ts DESC) AS ordem
        FROM leituras l
        JOIN sensores s ON s.id = l.id_sensor
        JOIN tipos_sensor tp ON tp.id = s.id_tipo
        WHERE s.id_tanque = :t AND s.status = 'ativo'
          AND tp.grandeza IN ('ph', 'temperatura')
          AND l.ts >= :desde AND l.ts <= :agora
    ) x
    WHERE ordem <= :n
    ORDER BY grandeza, ts DESC
    """
)
SQL_PREVISOES = text(
    """
    SELECT id, horizonte_h, valor_previsto, nivel_risco, confianca
    FROM previsoes
    WHERE id_tanque = :t AND ts_previsao = (
        SELECT max(ts_previsao) FROM previsoes WHERE id_tanque = :t AND ts_previsao >= :desde AND ts_previsao <= :agora
    )
    ORDER BY horizonte_h
    """
)
SQL_TANQUE = text(
    "SELECT t.nome, t.id_usuario, u.telefone FROM tanques t JOIN usuarios u ON u.id = t.id_usuario WHERE t.id = :t"
)
# nível, parâmetro e recomendação vão para o banco como foram enviados: é deles que o painel monta o alerta
SQL_INSERIR = text(
    "INSERT INTO alertas "
    "(id_previsao, id_tanque, id_usuario, mensagem, nivel_risco, parametro, recomendacao, canal, status, criado_em) "
    "VALUES (:p, :t, :u, :m, :nivel, :parametro, :recomendacao, 'whatsapp', 'pendente', :agora) RETURNING id"
)
SQL_ATUALIZAR = text("UPDATE alertas SET status = :status, ts_envio = :ts WHERE id = :id")


class MonitorAlertas:
    """Dispara só quando o caso muda. O primeiro caso depois de iniciar também sai: serve de sinal de que está no ar."""

    def __init__(self, fabrica_destino: Callable[[str], Destino], confianca_min: float) -> None:
        self._fabrica_destino = fabrica_destino
        self._confianca_min = confianca_min
        self._enviado: dict[int, str] = {}
        self._pendente: dict[int, tuple[str, int]] = {}

    def executar_ciclo(self, engine: Engine, agora: datetime | None = None) -> dict[str, int]:
        agora = agora or datetime.now(timezone.utc)
        contagem = {"enviados": 0, "falhas": 0}
        with engine.connect() as conn:
            url = conn.execute(SQL_WEBHOOK).scalar_one_or_none()
            tanques = tanques_ativos(conn)
        # sem webhook não avalia nada: ao configurar, o primeiro caso sai como se o serviço tivesse acabado de subir
        if not url:
            return contagem
        destino = self._fabrica_destino(url)
        for id_tanque, faixa in tanques:
            try:
                enviado = self._avaliar(engine, destino, id_tanque, faixa, agora)
            except Exception:
                # um tanque com problema não pode impedir o alerta dos outros
                logger.exception("tanque %d: erro ao avaliar alerta", id_tanque)
                contagem["falhas"] += 1
                continue
            if enviado is True:
                contagem["enviados"] += 1
            elif enviado is False:
                contagem["falhas"] += 1
        return contagem

    def _avaliar(
        self, engine: Engine, destino: Destino, id_tanque: int, faixa: FaixaEspecie, agora: datetime
    ) -> bool | None:
        with engine.connect() as conn:
            leituras, ts_leitura = self._ler_leituras(conn, id_tanque, agora)
            previsoes = conn.execute(
                SQL_PREVISOES, {"t": id_tanque, "desde": agora - PREVISAO_RECENTE, "agora": agora}
            ).all()
        od = next((p for p in previsoes if p.horizonte_h == 0), None)
        par_od = (float(od.valor_previsto), float(od.confianca)) if od else None

        caso = classificar(leituras, par_od, faixa, self._confianca_min, self._enviado.get(id_tanque))
        if caso is None or caso == self._enviado.get(id_tanque):
            self._pendente.pop(id_tanque, None)
            return None

        valores = {g: (leituras[g][0] if leituras.get(g) else None) for g in GRANDEZAS_MEDIDAS}
        valores["od"] = par_od[0] if par_od else None
        risco = {f"{p.horizonte_h}h": p.nivel_risco for p in previsoes if p.horizonte_h > 0}

        with engine.begin() as conn:
            tanque = conn.execute(SQL_TANQUE, {"t": id_tanque}).one()
            alerta = montar_alerta(
                caso, None, id_tanque, tanque.nome, tanque.telefone, valores,
                float(od.confianca) if od else None, risco, faixa, ts_leitura, agora,
            )
            pendente = self._pendente.get(id_tanque)
            # numa nova tentativa reaproveita a linha: uma falha de rede não vira vários alertas no histórico
            if pendente and pendente[0] == caso:
                id_alerta = pendente[1]
            else:
                id_alerta = conn.execute(
                    SQL_INSERIR,
                    {
                        "p": od.id if od else None, "t": id_tanque, "u": tanque.id_usuario,
                        "m": alerta["mensagem"], "nivel": alerta["nivel_risco"], "parametro": alerta["parametro"],
                        "recomendacao": alerta["recomendacao"], "agora": agora,
                    },
                ).scalar_one()
            alerta["id_alerta"] = id_alerta

        ok = destino.enviar(alerta)
        with engine.begin() as conn:
            conn.execute(SQL_ATUALIZAR, {"status": "enviado" if ok else "falha", "ts": agora if ok else None, "id": id_alerta})
        if ok:
            self._enviado[id_tanque] = caso
            self._pendente.pop(id_tanque, None)
            logger.info("tanque %d: alerta %d enviado (%s)", id_tanque, id_alerta, caso)
        else:
            self._pendente[id_tanque] = (caso, id_alerta)
            logger.warning("tanque %d: alerta %d nao enviado (%s); tenta no proximo ciclo", id_tanque, id_alerta, caso)
        return ok

    @staticmethod
    def _ler_leituras(conn: Connection, id_tanque: int, agora: datetime) -> tuple[dict[str, list[float]], datetime | None]:
        leituras: dict[str, list[float]] = {}
        mais_recente = None
        for grandeza, ts, valor in conn.execute(
            SQL_LEITURAS,
            {"t": id_tanque, "desde": agora - LEITURA_RECENTE, "agora": agora, "n": LEITURAS_PARA_ENCERRAR},
        ):
            leituras.setdefault(grandeza, []).append(float(valor))
            mais_recente = max(mais_recente, ts) if mais_recente else ts
        return leituras, mais_recente


EXEMPLOS = {
    "normal": {"ph": 8.1, "temperatura": 25.9, "od": 7.2},
    "ph_alto": {"ph": 9.18, "temperatura": 25.9, "od": 6.8},
    "ph_baixo": {"ph": 4.2, "temperatura": 25.9, "od": 5.1},
    "temperatura_alta": {"ph": 7.5, "temperatura": 32.4, "od": 6.1},
    "temperatura_baixa": {"ph": 7.5, "temperatura": 18.2, "od": 8.3},
    "od_baixo": {"ph": 7.5, "temperatura": 28.0, "od": 3.4},
}


def alerta_simulado(caso: str, faixa: FaixaEspecie, agora: datetime) -> dict:
    """Payload de exemplo para montar o workflow sem mexer no sensor; não grava em `alertas`."""
    alerta = montar_alerta(
        caso, 0, 1, "Tanque bancada TCC", None, EXEMPLOS[caso], 0.8,
        {"1h": "otimo", "2h": "otimo", "3h": "otimo"}, faixa, agora, agora,
    )
    alerta["simulado"] = True
    return alerta


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dispara alertas de qualidade da água para o webhook do N8N")
    parser.add_argument("--simular", choices=CASOS, help="envia só um exemplo deste caso, sem gravar alerta, e sai")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    engine = create_engine(settings.database_url)

    if args.simular:
        with engine.connect() as conn:
            url = conn.execute(SQL_WEBHOOK).scalar_one_or_none()
        if not url:
            raise SystemExit("configure a URL do webhook no painel, em Configurações")
        ok = Webhook(url, settings.alertas_webhook_token).enviar(
            alerta_simulado(args.simular, TILAPIA, datetime.now(timezone.utc))
        )
        print(f"exemplo '{args.simular}': {'enviado' if ok else 'NAO enviado'}")
        raise SystemExit(0 if ok else 1)

    monitor = MonitorAlertas(lambda url: Webhook(url, settings.alertas_webhook_token), settings.ml_confianca_min)
    logger.info("servico de alertas iniciado, ciclo a cada %d s", settings.alertas_intervalo_s)
    while True:
        try:
            monitor.executar_ciclo(engine)
        except Exception:
            # banco fora do ar, por exemplo: tenta de novo no próximo ciclo
            logger.exception("ciclo de alertas falhou")
        time.sleep(settings.alertas_intervalo_s)


if __name__ == "__main__":
    main()
