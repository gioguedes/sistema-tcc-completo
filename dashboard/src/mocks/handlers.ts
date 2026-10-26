/**
 * Servidor SIMULADO (MSW) que implementa o contrato descrito em docs/CONTRATO_API.md.
 * Substitui o backend FastAPI apenas enquanto ele não existe; nenhum código da interface
 * depende deste arquivo.
 */
import { delay, http, HttpResponse } from 'msw'
import type { Grandeza, NivelRisco, StatusSensor, StatusTanque } from '@/dominio/comum'
import { normalizarMac, normalizarTelefone } from '@/dominio/formularios'
import { abrirSessao, encerrarSessao, lerSessao, obterBanco, proximoId, salvarBanco } from './banco'
import {
  ACIONAMENTOS_AUTOMATICOS,
  ALERTAS,
  CENARIOS,
  ESPECIES,
  PREVISOES,
  TIPOS_SENSOR,
  UNIDADE_OD,
  type AcionamentoSimulado,
  type DispositivoSimulado,
  type TanqueSimulado,
  type UsuarioSimulado,
} from './dados'
import { nivelGeral, nivelPorFaixa } from './faixas'
import { gerarSerie, HORA, MINUTO, valorEm } from './series'

const API = '*/api/v1'
const VALIDADE_TOKEN_MS = 15 * MINUTO
/** Regra I-10 (a confirmar no backend): offline após 5 min sem leituras, como no fluxo alternativo do UC02. */
const LIMITE_OFFLINE_MS = 5 * MINUTO
/** Ciclo do serviço de ML (ML_INTERVALO_S = 300). */
const CICLO_ML_MS = 5 * MINUTO
const GRANDEZAS_FISICAS: Grandeza[] = ['ph', 'temperatura', 'turbidez']
const GRANDEZAS: Grandeza[] = ['ph', 'temperatura', 'turbidez', 'od']
const STATUS_TANQUE: StatusTanque[] = ['ativo', 'manutencao', 'inativo']
const STATUS_SENSOR: StatusSensor[] = ['ativo', 'inativo', 'em_calibracao']
const REGEX_MAC = /^[0-9a-f]{12}$/

type Corpo = Record<string, unknown>
type Problema = [caminho: string[], mensagem: string]

const iso = (t: number) => new Date(t).toISOString()

// ---------------------------------------------------------------- respostas no formato do FastAPI

const erro = (status: number, detail: unknown) => HttpResponse.json({ detail }, { status })

const erroDeCampos = (status: 409 | 422, problemas: Problema[]) =>
  erro(
    status,
    problemas.map(([caminho, msg]) => ({
      loc: ['body', ...caminho],
      msg,
      type: status === 409 ? 'conflict' : 'value_error',
    })),
  )

async function lerCorpo(request: Request): Promise<Corpo> {
  try {
    const corpo: unknown = await request.json()
    return corpo && typeof corpo === 'object' ? (corpo as Corpo) : {}
  } catch {
    return {}
  }
}

// ---------------------------------------------------------------- autenticação simulada

function emitirToken(idUsuario: number) {
  const expira = Date.now() + VALIDADE_TOKEN_MS
  return { access_token: `simulado.${idUsuario}.${expira}`, expira_em: iso(expira) }
}

function autorizar(request: Request, somenteAdmin = false): UsuarioSimulado | Response {
  const token = /^Bearer simulado\.(\d+)\.(\d+)$/.exec(request.headers.get('Authorization') ?? '')
  const usuario =
    token && Number(token[2]) > Date.now()
      ? obterBanco().usuarios.find((u) => u.id === Number(token[1]))
      : undefined
  if (!usuario) return erro(401, 'Não autenticado.')
  if (somenteAdmin && usuario.perfil !== 'admin') return erro(403, 'Acesso restrito a administradores.')
  return usuario
}

const semSenha = ({ senha: _senha, ...usuario }: UsuarioSimulado) => usuario

// ---------------------------------------------------------------- serialização

function fimDosDados(d: DispositivoSimulado, agora: number): number | null {
  if (d.cenario === null) return null
  return Math.floor((d.sem_dados_desde ?? agora) / MINUTO) * MINUTO
}

function statusConexao(d: DispositivoSimulado, agora: number) {
  const fim = fimDosDados(d, agora)
  return fim !== null && agora - fim <= LIMITE_OFFLINE_MS ? 'online' : 'offline'
}

function unidadeDe(g: Grandeza): string {
  return TIPOS_SENSOR.find((t) => t.grandeza === g)?.unidade ?? UNIDADE_OD
}

const dispositivosDoTanque = (idTanque: number) => obterBanco().dispositivos.filter((d) => d.id_tanque === idTanque)

/** Dispositivo cujas leituras representam o tanque (o mais recente com dados). */
function fonteDeDados(idTanque: number, agora: number) {
  return dispositivosDoTanque(idTanque)
    .map((d) => ({ d, fim: fimDosDados(d, agora) }))
    .filter((x): x is { d: DispositivoSimulado; fim: number } => x.fim !== null)
    .sort((a, b) => b.fim - a.fim)[0]
}

function todosAcionamentos(agora: number): AcionamentoSimulado[] {
  return [
    ...ACIONAMENTOS_AUTOMATICOS.map(({ minutosAtras, ...a }) => ({ ...a, ts: agora - minutosAtras * MINUTO })),
    ...obterBanco().acionamentos,
  ]
}

function serializarDispositivo(d: DispositivoSimulado, agora: number) {
  const fim = fimDosDados(d, agora)
  const ultimo = todosAcionamentos(agora)
    .filter((a) => a.id_dispositivo === d.id)
    .sort((a, b) => b.ts - a.ts)[0]
  return {
    id: d.id,
    id_tanque: d.id_tanque,
    nome: d.nome,
    modelo_esp32: d.modelo_esp32,
    mac_address: d.mac_address,
    versao_firmware: d.versao_firmware,
    ip_local: d.ip_local,
    status_conexao: statusConexao(d, agora),
    ultima_leitura_em: fim === null ? null : iso(fim),
    data_cadastro: d.data_cadastro,
    sensores: obterBanco()
      .sensores.filter((s) => s.id_dispositivo === d.id)
      .map((s) => {
        const tipo = TIPOS_SENSOR.find((t) => t.id === s.id_tipo)!
        return {
          id: s.id,
          grandeza: tipo.grandeza,
          modelo: tipo.modelo,
          unidade: tipo.unidade,
          status: s.status,
          data_instalacao: s.data_instalacao,
        }
      }),
    ultimo_acionamento: ultimo
      ? { id: ultimo.id, acao: ultimo.acao, motivo: ultimo.motivo, ts_acionamento: iso(ultimo.ts), automatico: ultimo.automatico }
      : null,
  }
}

/** Fim dos dados de uma grandeza: o nó pode estar no ar com um sensor em falha (payload com `null`). */
function fimDaGrandeza(d: DispositivoSimulado, g: Grandeza, fim: number): number {
  const falha = d.falhas[g]
  return falha === undefined ? fim : Math.min(fim, Math.floor(falha / MINUTO) * MINUTO)
}

/**
 * Situação do tanque como o backend real a teria: leituras do nó e, se o serviço de ML
 * roda para ele (tanque `ativo`, com espécie, nó enviando dados), a última estimativa de OD (h = 0).
 */
function estadoDoTanque(t: TanqueSimulado, agora: number) {
  const especie = ESPECIES.find((e) => e.id === t.id_especie) ?? null
  const fonte = fonteDeDados(t.id, agora)
  const online = fonte ? agora - fonte.fim <= LIMITE_OFFLINE_MS : false
  const cenario = fonte ? CENARIOS[fonte.d.cenario!]! : null
  const previsao = PREVISOES[t.id]
  const comPrevisao = Boolean(t.status === 'ativo' && especie && online && cenario && previsao)
  const ciclo = Math.floor(agora / CICLO_ML_MS) * CICLO_ML_MS
  const valor = (g: Grandeza, ts: number) => valorEm(cenario!, g, ts, agora)

  let odAtual: { valor: number; nivel: NivelRisco; confianca: number; baixa: boolean; ts: number } | null = null
  let nivelAtual: NivelRisco | null = null
  if (comPrevisao && especie && fonte && previsao) {
    const od = valor('od', ciclo)
    const confianca = Number(previsao.confiancaOd)
    odAtual = { valor: od, nivel: nivelPorFaixa(od, 'od', especie), confianca, baixa: confianca < 0.5, ts: ciclo }
    nivelAtual = nivelGeral(valor('ph', fonte.fim), valor('temperatura', fonte.fim), od, especie)
  }
  return { especie, fonte, cenario, comPrevisao, previsao, odAtual, nivelAtual, valor }
}

function serializarTanque(t: TanqueSimulado, agora: number) {
  const { especie, fonte, odAtual, nivelAtual, valor } = estadoDoTanque(t, agora)
  const fisicas = fonte
    ? GRANDEZAS_FISICAS.map((g) => {
        const ts = fimDaGrandeza(fonte.d, g, fonte.fim)
        return { grandeza: g, valor: String(valor(g, ts)), unidade: unidadeDe(g), ts: iso(ts), estimado: false }
      })
    : []
  const od = odAtual
    ? [
        {
          grandeza: 'od',
          valor: odAtual.valor.toFixed(4),
          unidade: UNIDADE_OD,
          ts: iso(odAtual.ts),
          estimado: true,
          baixa_confianca: odAtual.baixa,
        },
      ]
    : []
  return {
    id: t.id,
    nome: t.nome,
    volume_litros: t.volume_litros.toFixed(2),
    quantidade_peixes: t.quantidade_peixes,
    data_povoamento: t.data_povoamento,
    status: t.status,
    criado_em: t.criado_em,
    especie,
    nivel_risco: nivelAtual,
    ultima_leitura_em: fonte ? iso(fonte.fim) : null,
    ultimas_leituras: [...fisicas, ...od],
    dispositivos: dispositivosDoTanque(t.id).map((d) => {
      const fim = fimDosDados(d, agora)
      return { id: d.id, nome: d.nome, status_conexao: statusConexao(d, agora), ultima_leitura_em: fim === null ? null : iso(fim) }
    }),
  }
}

function nomeDoTanque(id: number) {
  return obterBanco().tanques.find((t) => t.id === id)?.nome ?? `Tanque ${id}`
}

function serializarAlerta(a: (typeof ALERTAS)[number], agora: number) {
  const criado = agora - a.minutosAtras * MINUTO
  return {
    id: a.id,
    id_tanque: a.id_tanque,
    tanque_nome: nomeDoTanque(a.id_tanque),
    id_previsao: 1000 + a.id,
    mensagem: a.mensagem,
    recomendacoes: a.recomendacoes,
    nivel_risco: a.nivel,
    parametro: a.parametro,
    canal: 'whatsapp',
    status: a.status,
    ts_envio: a.segundosAteEnvio === null ? null : iso(criado + a.segundosAteEnvio * 1000),
    criado_em: iso(criado),
  }
}

function paginar<T>(itens: T[], url: URL) {
  const pagina = Math.max(1, Number(url.searchParams.get('pagina')) || 1)
  const porPagina = Math.min(50, Math.max(1, Number(url.searchParams.get('por_pagina')) || 10))
  return {
    itens: itens.slice((pagina - 1) * porPagina, pagina * porPagina),
    total: itens.length,
    pagina,
    por_pagina: porPagina,
  }
}

// ---------------------------------------------------------------- validação do lado do "servidor"

function validarTanque(c: Corpo): Problema[] {
  const problemas: Problema[] = []
  if (typeof c.nome !== 'string' || !c.nome.trim()) problemas.push([['nome'], 'Informe o nome do tanque.'])
  if (typeof c.volume_litros !== 'number' || !(c.volume_litros > 0))
    problemas.push([['volume_litros'], 'O volume deve ser maior que zero.'])
  if (!Number.isInteger(c.quantidade_peixes) || (c.quantidade_peixes as number) < 0)
    problemas.push([['quantidade_peixes'], 'A quantidade não pode ser negativa.'])
  if (!ESPECIES.some((e) => e.id === c.id_especie)) problemas.push([['id_especie'], 'Selecione uma espécie do catálogo.'])
  if (!STATUS_TANQUE.includes(c.status as StatusTanque)) problemas.push([['status'], 'Status inválido.'])
  return problemas
}

function validarDispositivo(c: Corpo, prefixo: string[] = [], ignorarId?: number): { problemas: Problema[]; conflito: boolean } {
  const problemas: Problema[] = []
  if (typeof c.nome !== 'string' || !c.nome.trim()) problemas.push([[...prefixo, 'nome'], 'Informe o nome do dispositivo.'])
  const mac = typeof c.mac_address === 'string' ? normalizarMac(c.mac_address) : ''
  if (!REGEX_MAC.test(mac.replace(/:/g, ''))) {
    problemas.push([[...prefixo, 'mac_address'], 'Endereço MAC inválido.'])
  } else if (obterBanco().dispositivos.some((d) => d.mac_address === mac && d.id !== ignorarId)) {
    return {
      problemas: [[[...prefixo, 'mac_address'], 'Este endereço MAC já está cadastrado em outro dispositivo.']],
      conflito: true,
    }
  }
  return { problemas, conflito: false }
}

function gravarDispositivo(c: Corpo, idTanque: number, agora: number): DispositivoSimulado {
  const banco = obterBanco()
  const novo: DispositivoSimulado = {
    id: proximoId(banco.dispositivos),
    id_tanque: idTanque,
    nome: String(c.nome).trim(),
    modelo_esp32: typeof c.modelo_esp32 === 'string' && c.modelo_esp32.trim() ? c.modelo_esp32.trim() : 'ESP32 DevKitC V4',
    mac_address: normalizarMac(String(c.mac_address)),
    versao_firmware: typeof c.versao_firmware === 'string' && c.versao_firmware ? c.versao_firmware : null,
    ip_local: typeof c.ip_local === 'string' && c.ip_local ? c.ip_local : null,
    data_cadastro: iso(agora),
    cenario: null,
    sem_dados_desde: null,
    falhas: {},
  }
  banco.dispositivos.push(novo)
  // Decisão I-07: os três sensores físicos são criados junto com o dispositivo.
  for (const tipo of TIPOS_SENSOR) {
    banco.sensores.push({
      id: proximoId(banco.sensores),
      id_dispositivo: novo.id,
      id_tipo: tipo.id,
      id_tanque: idTanque,
      data_instalacao: iso(agora).slice(0, 10),
      status: 'ativo',
    })
  }
  return novo
}

const dadosDoTanque = (c: Corpo) => ({
  nome: String(c.nome).trim(),
  id_especie: c.id_especie as number,
  volume_litros: c.volume_litros as number,
  quantidade_peixes: c.quantidade_peixes as number,
  data_povoamento: typeof c.data_povoamento === 'string' && c.data_povoamento ? c.data_povoamento : null,
  status: c.status as StatusTanque,
})

// ---------------------------------------------------------------- rotas

export const handlers = [
  http.post(`${API}/auth/login`, async ({ request }) => {
    await delay()
    const corpo = await lerCorpo(request)
    const email = typeof corpo.email === 'string' ? corpo.email.trim().toLowerCase() : ''
    const usuario = obterBanco().usuarios.find((u) => u.email === email && u.senha === corpo.senha)
    if (!usuario) return erro(401, 'E-mail ou senha incorretos.')
    abrirSessao(usuario.id, corpo.lembrar === true)
    return HttpResponse.json(emitirToken(usuario.id))
  }),

  http.post(`${API}/auth/refresh`, async () => {
    await delay()
    const id = lerSessao()
    const usuario = obterBanco().usuarios.find((u) => u.id === id)
    if (!usuario) return erro(401, 'Sessão expirada.')
    return HttpResponse.json(emitirToken(usuario.id))
  }),

  http.post(`${API}/auth/logout`, async () => {
    await delay()
    encerrarSessao()
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${API}/auth/eu`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    return HttpResponse.json(semSenha(usuario))
  }),

  http.patch(`${API}/auth/eu`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const corpo = await lerCorpo(request)
    const problemas: Problema[] = []
    if (typeof corpo.nome !== 'string' || !corpo.nome.trim()) problemas.push([['nome'], 'Informe seu nome.'])
    const telefone = typeof corpo.telefone === 'string' && corpo.telefone ? normalizarTelefone(corpo.telefone) : null
    if (typeof corpo.telefone === 'string' && corpo.telefone && !telefone)
      problemas.push([['telefone'], 'Telefone inválido.'])
    if (problemas.length) return erroDeCampos(422, problemas)
    usuario.nome = String(corpo.nome).trim()
    usuario.telefone = telefone
    salvarBanco()
    return HttpResponse.json(semSenha(usuario))
  }),

  http.get(`${API}/especies`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    return HttpResponse.json(ESPECIES)
  }),

  http.get(`${API}/tanques`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const agora = Date.now()
    return HttpResponse.json(obterBanco().tanques.map((t) => serializarTanque(t, agora)))
  }),

  http.get(`${API}/tanques/:id`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const tanque = obterBanco().tanques.find((t) => t.id === Number(params.id))
    if (!tanque) return erro(404, 'Tanque não encontrado.')
    return HttpResponse.json(serializarTanque(tanque, Date.now()))
  }),

  http.post(`${API}/tanques`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request, true)
    if (usuario instanceof Response) return usuario
    const corpo = await lerCorpo(request)
    const problemas = validarTanque(corpo)
    const dispositivo = corpo.dispositivo && typeof corpo.dispositivo === 'object' ? (corpo.dispositivo as Corpo) : null
    if (dispositivo) {
      const validacao = validarDispositivo(dispositivo, ['dispositivo'])
      if (validacao.conflito) return erroDeCampos(409, validacao.problemas)
      problemas.push(...validacao.problemas)
    }
    if (problemas.length) return erroDeCampos(422, problemas)

    const agora = Date.now()
    const banco = obterBanco()
    const tanque: TanqueSimulado = { id: proximoId(banco.tanques), id_usuario: usuario.id, ...dadosDoTanque(corpo), criado_em: iso(agora) }
    banco.tanques.push(tanque)
    if (dispositivo) gravarDispositivo(dispositivo, tanque.id, agora)
    salvarBanco()
    return HttpResponse.json(serializarTanque(tanque, agora), { status: 201 })
  }),

  http.patch(`${API}/tanques/:id`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request, true)
    if (usuario instanceof Response) return usuario
    const tanque = obterBanco().tanques.find((t) => t.id === Number(params.id))
    if (!tanque) return erro(404, 'Tanque não encontrado.')
    const corpo = await lerCorpo(request)
    const problemas = validarTanque(corpo)
    if (problemas.length) return erroDeCampos(422, problemas)
    Object.assign(tanque, dadosDoTanque(corpo))
    salvarBanco()
    return HttpResponse.json(serializarTanque(tanque, Date.now()))
  }),

  http.get(`${API}/tanques/:id/dispositivos`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const id = Number(params.id)
    if (!obterBanco().tanques.some((t) => t.id === id)) return erro(404, 'Tanque não encontrado.')
    const agora = Date.now()
    return HttpResponse.json(dispositivosDoTanque(id).map((d) => serializarDispositivo(d, agora)))
  }),

  http.post(`${API}/dispositivos`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request, true)
    if (usuario instanceof Response) return usuario
    const corpo = await lerCorpo(request)
    const idTanque = Number(corpo.id_tanque)
    if (!obterBanco().tanques.some((t) => t.id === idTanque))
      return erroDeCampos(422, [[['id_tanque'], 'Tanque não encontrado.']])
    const validacao = validarDispositivo(corpo)
    if (validacao.conflito) return erroDeCampos(409, validacao.problemas)
    if (validacao.problemas.length) return erroDeCampos(422, validacao.problemas)
    const agora = Date.now()
    const novo = gravarDispositivo(corpo, idTanque, agora)
    salvarBanco()
    return HttpResponse.json(serializarDispositivo(novo, agora), { status: 201 })
  }),

  http.patch(`${API}/dispositivos/:id`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request, true)
    if (usuario instanceof Response) return usuario
    const dispositivo = obterBanco().dispositivos.find((d) => d.id === Number(params.id))
    if (!dispositivo) return erro(404, 'Dispositivo não encontrado.')
    const corpo = await lerCorpo(request)
    const validacao = validarDispositivo(corpo, [], dispositivo.id)
    if (validacao.conflito) return erroDeCampos(409, validacao.problemas)
    if (validacao.problemas.length) return erroDeCampos(422, validacao.problemas)
    Object.assign(dispositivo, {
      nome: String(corpo.nome).trim(),
      mac_address: normalizarMac(String(corpo.mac_address)),
      modelo_esp32: typeof corpo.modelo_esp32 === 'string' && corpo.modelo_esp32 ? corpo.modelo_esp32 : dispositivo.modelo_esp32,
      versao_firmware: typeof corpo.versao_firmware === 'string' && corpo.versao_firmware ? corpo.versao_firmware : null,
      ip_local: typeof corpo.ip_local === 'string' && corpo.ip_local ? corpo.ip_local : null,
    })
    salvarBanco()
    return HttpResponse.json(serializarDispositivo(dispositivo, Date.now()))
  }),

  http.patch(`${API}/sensores/:id`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request, true)
    if (usuario instanceof Response) return usuario
    const sensor = obterBanco().sensores.find((s) => s.id === Number(params.id))
    if (!sensor) return erro(404, 'Sensor não encontrado.')
    const corpo = await lerCorpo(request)
    if (!STATUS_SENSOR.includes(corpo.status as StatusSensor)) return erroDeCampos(422, [[['status'], 'Status inválido.']])
    sensor.status = corpo.status as StatusSensor
    salvarBanco()
    const tipo = TIPOS_SENSOR.find((t) => t.id === sensor.id_tipo)!
    return HttpResponse.json({
      id: sensor.id,
      grandeza: tipo.grandeza,
      modelo: tipo.modelo,
      unidade: tipo.unidade,
      status: sensor.status,
      data_instalacao: sensor.data_instalacao,
    })
  }),

  http.post(`${API}/dispositivos/:id/aerador`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const banco = obterBanco()
    const dispositivo = banco.dispositivos.find((d) => d.id === Number(params.id))
    if (!dispositivo) return erro(404, 'Dispositivo não encontrado.')
    const { acao } = await lerCorpo(request)
    if (acao !== 'ligar' && acao !== 'desligar') return erroDeCampos(422, [[['acao'], 'Ação inválida.']])
    const acionamento: AcionamentoSimulado = {
      id: proximoId([...ACIONAMENTOS_AUTOMATICOS, ...banco.acionamentos]),
      id_dispositivo: dispositivo.id,
      id_tanque: dispositivo.id_tanque,
      acao,
      automatico: false,
      motivo: `Comando manual enviado por ${usuario.nome}.`,
      ts: Date.now(),
    }
    banco.acionamentos.push(acionamento)
    salvarBanco()
    return HttpResponse.json(
      { id: acionamento.id, acao: acionamento.acao, motivo: acionamento.motivo, ts_acionamento: iso(acionamento.ts) },
      { status: 202 },
    )
  }),

  http.get(`${API}/tanques/:id/leituras`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const idTanque = Number(params.id)
    if (!obterBanco().tanques.some((t) => t.id === idTanque)) return erro(404, 'Tanque não encontrado.')

    const url = new URL(request.url)
    const desde = Date.parse(url.searchParams.get('desde') ?? '')
    const ate = Date.parse(url.searchParams.get('ate') ?? '')
    const bucket = url.searchParams.get('bucket') ?? 'raw'
    const passo = bucket === 'raw' ? MINUTO : bucket === '5m' ? 5 * MINUTO : bucket === '1h' ? HORA : NaN
    if (Number.isNaN(desde) || Number.isNaN(ate) || desde >= ate || Number.isNaN(passo))
      return erro(422, [{ loc: ['query'], msg: 'Parâmetros de consulta inválidos.', type: 'value_error' }])
    if ((ate - desde) / passo > 5000)
      return erro(422, [{ loc: ['query', 'bucket'], msg: 'Intervalo grande demais para esse agrupamento.', type: 'value_error' }])

    const pedidas = url.searchParams.get('grandezas')?.split(',') ?? GRANDEZAS
    const grandezas = GRANDEZAS.filter((g) => pedidas.includes(g))
    const agora = Date.now()
    const tanque = obterBanco().tanques.find((t) => t.id === idTanque)!
    const { fonte, cenario, comPrevisao } = estadoDoTanque(tanque, agora)
    const inicio = fonte ? Math.max(desde, Date.parse(fonte.d.data_cadastro)) : 0

    const pontos = (g: Grandeza) => {
      if (!fonte || !cenario) return []
      // OD: série das linhas h = 0 de `previsoes`, uma por ciclo do serviço de ML
      if (g === 'od') {
        if (!comPrevisao) return []
        const fimOd = Math.min(ate, Math.floor(agora / CICLO_ML_MS) * CICLO_ML_MS)
        return inicio <= fimOd ? gerarSerie(cenario, g, inicio, fimOd, Math.max(passo, CICLO_ML_MS), agora) : []
      }
      const fim = Math.min(ate, fimDaGrandeza(fonte.d, g, fonte.fim))
      return inicio <= fim ? gerarSerie(cenario, g, inicio, fim, passo, agora) : []
    }

    return HttpResponse.json({
      id_tanque: idTanque,
      bucket,
      desde: iso(desde),
      ate: iso(ate),
      series: grandezas.map((g) => ({ grandeza: g, unidade: unidadeDe(g), estimado: g === 'od', pontos: pontos(g) })),
    })
  }),

  http.get(`${API}/tanques/:id/previsoes/atual`, async ({ request, params }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const idTanque = Number(params.id)
    const tanque = obterBanco().tanques.find((t) => t.id === idTanque)
    if (!tanque) return erro(404, 'Tanque não encontrado.')
    const agora = Date.now()
    const { odAtual, nivelAtual, previsao } = estadoDoTanque(tanque, agora)
    if (!odAtual || !previsao) {
      // o serviço de ML não grava quando os dados não bastam (indeterminado, UC06)
      return HttpResponse.json({ id_tanque: idTanque, nivel_risco: null, gerada_em: null, od_atual: null, horizontes: [] })
    }
    const gerada = iso(odAtual.ts)
    return HttpResponse.json({
      id_tanque: idTanque,
      nivel_risco: nivelAtual,
      gerada_em: gerada,
      od_atual: {
        valor: odAtual.valor.toFixed(4),
        nivel_risco: odAtual.nivel,
        confianca: odAtual.confianca.toFixed(4),
        baixa_confianca: odAtual.baixa,
      },
      horizontes: previsao.horizontes.map((h, i) => ({
        id: idTanque * 10 + i + 1,
        parametro_critico: h.parametro,
        valor_previsto: h.valor,
        nivel_risco: h.nivel,
        horizonte_h: i + 1,
        confianca: h.probabilidade,
        baixa_confianca: false,
        ts_previsao: gerada,
      })),
    })
  }),

  http.get(`${API}/alertas`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const url = new URL(request.url)
    const agora = Date.now()
    const tanque = Number(url.searchParams.get('tanque')) || null
    const status = url.searchParams.get('status')
    let alertas = [...ALERTAS].sort((a, b) => a.minutosAtras - b.minutosAtras)
    if (tanque) alertas = alertas.filter((a) => a.id_tanque === tanque)
    if (status) alertas = alertas.filter((a) => a.status === status)
    const desde = Date.parse(url.searchParams.get('desde') ?? '')
    const ate = Date.parse(url.searchParams.get('ate') ?? '')
    if (!Number.isNaN(desde)) alertas = alertas.filter((a) => agora - a.minutosAtras * MINUTO >= desde)
    if (!Number.isNaN(ate)) alertas = alertas.filter((a) => agora - a.minutosAtras * MINUTO <= ate)
    if (url.searchParams.get('ativos') === 'true') {
      // "Ativo" (regra a definir no backend — F-10): último alerta de cada tanque que segue em atenção/crítico.
      const tanquesEmRisco = new Set(
        obterBanco()
          .tanques.map((t) => serializarTanque(t, agora))
          .filter((t) => t.nivel_risco === 'atencao' || t.nivel_risco === 'critico')
          .map((t) => t.id),
      )
      const vistos = new Set<number>()
      alertas = alertas.filter((a) => {
        if (!tanquesEmRisco.has(a.id_tanque) || vistos.has(a.id_tanque)) return false
        vistos.add(a.id_tanque)
        return true
      })
    }
    return HttpResponse.json(paginar(alertas.map((a) => serializarAlerta(a, agora)), url))
  }),

  http.get(`${API}/eventos`, async ({ request }) => {
    await delay()
    const usuario = autorizar(request)
    if (usuario instanceof Response) return usuario
    const agora = Date.now()
    const eventos = [
      ...ALERTAS.map((a) => ({
        tipo: 'alerta' as const,
        id: `alerta-${a.id}`,
        id_tanque: a.id_tanque,
        tanque_nome: nomeDoTanque(a.id_tanque),
        ocorrido_em: agora - a.minutosAtras * MINUTO,
        nivel_risco: a.nivel,
        mensagem: a.mensagem,
      })),
      ...todosAcionamentos(agora).map((a) => ({
        tipo: 'acionamento' as const,
        id: `acionamento-${a.id}`,
        id_tanque: a.id_tanque,
        tanque_nome: nomeDoTanque(a.id_tanque),
        ocorrido_em: a.ts,
        acao: a.acao,
        automatico: a.automatico,
        motivo: a.motivo,
      })),
    ]
      .sort((a, b) => b.ocorrido_em - a.ocorrido_em)
      .map((e) => ({ ...e, ocorrido_em: iso(e.ocorrido_em) }))
    return HttpResponse.json(paginar(eventos, new URL(request.url)))
  }),
]
