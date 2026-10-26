/**
 * Dados SIMULADOS para desenvolver o front-end enquanto a API não existe.
 * Estrutura idêntica às tabelas do Apêndice A; valores fictícios.
 * Espécie e tipos de sensor copiados do seed do backend (src/db/seed.py).
 */
import type { Grandeza, NivelRisco, Perfil, StatusSensor, StatusTanque } from '@/dominio/comum'
import { DIA, MINUTO, type CenarioSerie } from './series'

export interface UsuarioSimulado {
  id: number
  nome: string
  email: string
  senha: string
  telefone: string | null
  perfil: Perfil
}

export interface TanqueSimulado {
  id: number
  id_usuario: number
  id_especie: number | null
  nome: string
  volume_litros: number
  quantidade_peixes: number
  data_povoamento: string | null
  status: StatusTanque
  criado_em: string
}

export interface DispositivoSimulado {
  id: number
  id_tanque: number
  nome: string
  modelo_esp32: string
  mac_address: string
  versao_firmware: string | null
  ip_local: string | null
  data_cadastro: string
  /** Índice em CENARIOS; dispositivos novos não têm leituras simuladas. */
  cenario: number | null
  /** Momento da última leitura recebida, quando o nó parou de enviar dados. */
  sem_dados_desde: number | null
  /** Sensor em falha: o firmware publica `null` e a ingestão para de gravar essa grandeza. */
  falhas: Partial<Record<Grandeza, number>>
}

export interface SensorSimulado {
  id: number
  id_dispositivo: number
  id_tipo: number
  id_tanque: number
  data_instalacao: string
  status: StatusSensor
}

export interface AcionamentoSimulado {
  id: number
  id_dispositivo: number
  id_tanque: number
  acao: 'ligar' | 'desligar'
  automatico: boolean
  motivo: string | null
  ts: number
}

/** Usuários de demonstração — credenciais documentadas no README. */
export const USUARIOS_INICIAIS: UsuarioSimulado[] = [
  {
    id: 1,
    nome: 'Carla Mendes',
    email: 'admin@painelaquicola.test',
    senha: 'aquicola-demo',
    telefone: '+5511912345678',
    perfil: 'admin',
  },
  {
    id: 2,
    nome: 'Marina Souza',
    email: 'produtor@painelaquicola.test',
    senha: 'aquicola-demo',
    telefone: null,
    perfil: 'operador',
  },
]

export const ESPECIES = [
  {
    id: 1,
    nome_comum: 'Tilápia do Nilo',
    nome_cientifico: 'Oreochromis niloticus',
    ph_min: '6.50',
    ph_max: '8.50',
    temp_min: '20.0',
    temp_max: '30.0',
    od_min: '4.00',
    od_max: '8.00',
  },
]

export const TIPOS_SENSOR: { id: number; grandeza: Grandeza; modelo: string; unidade: string }[] = [
  { id: 1, grandeza: 'ph', modelo: 'SEN0161-V2', unidade: 'pH' },
  { id: 2, grandeza: 'temperatura', modelo: 'DS18B20', unidade: 'C' },
  { id: 3, grandeza: 'turbidez', modelo: 'SEN0189', unidade: 'NTU' },
]

export const UNIDADE_OD = 'mg/L'

const p = (base: number, amplitude: number, pico: number, ruido: number, deriva: number, casas: number, min = 0, max = 3000) => ({
  base,
  amplitude,
  pico,
  ruido,
  deriva,
  casas,
  min,
  max,
})

export const CENARIOS: CenarioSerie[] = [
  {
    semente: 11,
    parametros: {
      temperatura: p(25.2, 0.8, 15, 0.08, 0.4, 1, -10, 50),
      ph: p(7.2, 0.15, 16, 0.03, 0.08, 2, 0, 14),
      turbidez: p(8, 1, 13, 0.6, 1.5, 1),
      od: p(6.3, 0.6, 16, 0.05, 0.3, 2, 0, 20),
    },
  },
  {
    semente: 23,
    parametros: {
      temperatura: p(26.4, 0.7, 15, 0.08, 0.4, 1, -10, 50),
      ph: p(8.15, 0.05, 16, 0.02, 0.04, 2, 0, 14),
      turbidez: p(14, 1.5, 13, 0.8, 2, 1),
      od: p(5.6, 0.3, 16, 0.05, 0.2, 2, 0, 20),
    },
    rampa: { grandeza: 'ph', variacao: 0.2, horas: 3 },
  },
  {
    semente: 37,
    parametros: {
      temperatura: p(28.4, 0.6, 15, 0.08, 0.3, 1, -10, 50),
      ph: p(7.8, 0.08, 16, 0.02, 0.05, 2, 0, 14),
      turbidez: p(35, 4, 13, 2, 4, 1),
      od: p(3.05, 0.2, 16, 0.04, 0.1, 2, 0, 20),
    },
    rampa: { grandeza: 'od', variacao: -0.25, horas: 3 },
  },
  {
    semente: 41,
    parametros: {
      temperatura: p(25.8, 0.5, 15, 0.08, 0.3, 1, -10, 50),
      ph: p(7.0, 0.1, 16, 0.03, 0.05, 2, 0, 14),
      turbidez: p(10, 1, 13, 0.6, 1, 1),
      od: p(5.8, 0.5, 16, 0.05, 0.2, 2, 0, 20),
    },
  },
]

interface HorizonteSimulado {
  parametro: Grandeza
  /** Projeção linear indicativa (spec do ML: inclinação de 60 min, presa na faixa física). */
  valor: string
  nivel: NivelRisco
  /** Probabilidade da classe prevista pelo classificador. */
  probabilidade: string
}

/**
 * Saída simulada do serviço de ML (UC06) por tanque. O nível atual e o nível do OD (h = 0)
 * são calculados pelos valores do cenário com a mesma regra de `ml/src/faixas.py`.
 * Tanques sem entrada aqui não recebem previsão.
 */
export const PREVISOES: Record<number, { confiancaOd: string; horizontes: HorizonteSimulado[] }> = {
  1: {
    confiancaOd: '0.8300',
    horizontes: [
      { parametro: 'ph', valor: '7.20', nivel: 'otimo', probabilidade: '0.9100' },
      { parametro: 'ph', valor: '7.21', nivel: 'otimo', probabilidade: '0.8800' },
      { parametro: 'ph', valor: '7.22', nivel: 'otimo', probabilidade: '0.8400' },
    ],
  },
  2: {
    confiancaOd: '0.7800',
    horizontes: [
      { parametro: 'ph', valor: '8.42', nivel: 'atencao', probabilidade: '0.8100' },
      { parametro: 'ph', valor: '8.49', nivel: 'atencao', probabilidade: '0.6900' },
      { parametro: 'ph', valor: '8.56', nivel: 'critico', probabilidade: '0.6200' },
    ],
  },
  3: {
    // abaixo de ML_CONFIANCA_MIN (0,5): estimativa de baixa confiança (UC06, fluxo alternativo)
    confiancaOd: '0.4600',
    horizontes: [
      { parametro: 'od', valor: '2.60', nivel: 'critico', probabilidade: '0.9400' },
      { parametro: 'od', valor: '2.40', nivel: 'critico', probabilidade: '0.9100' },
      { parametro: 'od', valor: '2.30', nivel: 'critico', probabilidade: '0.8700' },
    ],
  },
}

interface AlertaSimulado {
  id: number
  id_tanque: number
  minutosAtras: number
  nivel: NivelRisco
  parametro: Grandeza
  mensagem: string
  recomendacoes: string[]
  status: 'pendente' | 'enviado' | 'falha'
  /** Segundos entre a criação e o envio pelo WhatsApp (RNF01: ≤ 60 s). */
  segundosAteEnvio: number | null
}

const RECOMENDACOES_OD = ['Ligue o aerador agora.', 'Reduza a ração de hoje.']

export const ALERTAS: AlertaSimulado[] = [
  { id: 14, id_tanque: 3, minutosAtras: 25, nivel: 'critico', parametro: 'od', mensagem: 'Oxigênio muito baixo (2,8 mg/L, estimado).', recomendacoes: RECOMENDACOES_OD, status: 'enviado', segundosAteEnvio: 38 },
  { id: 13, id_tanque: 2, minutosAtras: 95, nivel: 'atencao', parametro: 'ph', mensagem: 'pH subindo (8,3). Tendência de alta nas próximas 3 horas.', recomendacoes: [], status: 'enviado', segundosAteEnvio: 41 },
  { id: 12, id_tanque: 3, minutosAtras: 360, nivel: 'atencao', parametro: 'temperatura', mensagem: 'Temperatura acima do ideal (29,4 °C).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 35 },
  { id: 11, id_tanque: 3, minutosAtras: 1290, nivel: 'critico', parametro: 'od', mensagem: 'Oxigênio muito baixo (2,6 mg/L, estimado).', recomendacoes: RECOMENDACOES_OD, status: 'falha', segundosAteEnvio: null },
  { id: 10, id_tanque: 2, minutosAtras: 1500, nivel: 'atencao', parametro: 'od', mensagem: 'Oxigênio em queda (4,1 mg/L, estimado).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 52 },
  { id: 9, id_tanque: 1, minutosAtras: 3080, nivel: 'atencao', parametro: 'turbidez', mensagem: 'Turbidez em alta (24 NTU).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 44 },
  { id: 8, id_tanque: 3, minutosAtras: 3480, nivel: 'critico', parametro: 'od', mensagem: 'Oxigênio muito baixo (2,7 mg/L, estimado).', recomendacoes: RECOMENDACOES_OD, status: 'enviado', segundosAteEnvio: 47 },
  { id: 7, id_tanque: 2, minutosAtras: 4420, nivel: 'atencao', parametro: 'temperatura', mensagem: 'Temperatura acima do ideal (29,1 °C).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 39 },
  { id: 6, id_tanque: 3, minutosAtras: 5220, nivel: 'atencao', parametro: 'od', mensagem: 'Oxigênio em queda (3,6 mg/L, estimado).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 33 },
  { id: 5, id_tanque: 1, minutosAtras: 6060, nivel: 'atencao', parametro: 'ph', mensagem: 'pH abaixo do ideal (6,6).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 40 },
  { id: 4, id_tanque: 2, minutosAtras: 7700, nivel: 'critico', parametro: 'od', mensagem: 'Oxigênio muito baixo (2,9 mg/L, estimado).', recomendacoes: RECOMENDACOES_OD, status: 'enviado', segundosAteEnvio: 36 },
  { id: 3, id_tanque: 3, minutosAtras: 8700, nivel: 'atencao', parametro: 'turbidez', mensagem: 'Turbidez em alta (41 NTU).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 45 },
  { id: 2, id_tanque: 1, minutosAtras: 10200, nivel: 'atencao', parametro: 'temperatura', mensagem: 'Temperatura acima do ideal (29,8 °C).', recomendacoes: [], status: 'enviado', segundosAteEnvio: 50 },
  { id: 1, id_tanque: 3, minutosAtras: 11800, nivel: 'critico', parametro: 'od', mensagem: 'Oxigênio muito baixo (2,8 mg/L, estimado).', recomendacoes: RECOMENDACOES_OD, status: 'enviado', segundosAteEnvio: 42 },
]

/** Acionamentos automáticos do relé (TC1: aerador liga com OD estimado abaixo de 3 mg/L). */
export const ACIONAMENTOS_AUTOMATICOS: (Omit<AcionamentoSimulado, 'ts'> & { minutosAtras: number })[] = [
  { id: 3, id_dispositivo: 3, id_tanque: 3, acao: 'ligar', automatico: true, motivo: 'Ação automática: oxigênio estimado abaixo de 3 mg/L.', minutosAtras: 140 },
  { id: 2, id_dispositivo: 3, id_tanque: 3, acao: 'desligar', automatico: true, motivo: 'Ação automática: oxigênio estimado normalizado.', minutosAtras: 1180 },
  { id: 1, id_dispositivo: 3, id_tanque: 3, acao: 'ligar', automatico: true, motivo: 'Ação automática: oxigênio estimado abaixo de 3 mg/L.', minutosAtras: 1285 },
]

export function criarDadosIniciais(agora: number) {
  const iso = (t: number) => new Date(t).toISOString()
  const criadoEm = iso(agora - 60 * DIA)
  const dataInstalacao = criadoEm.slice(0, 10)

  const tanques: TanqueSimulado[] = [
    { id: 1, id_usuario: 2, id_especie: 1, nome: 'Tanque Norte', volume_litros: 500, quantidade_peixes: 40, data_povoamento: '2026-08-10', status: 'ativo', criado_em: criadoEm },
    { id: 2, id_usuario: 2, id_especie: 1, nome: 'Tanque Sul', volume_litros: 500, quantidade_peixes: 35, data_povoamento: '2026-08-10', status: 'ativo', criado_em: criadoEm },
    { id: 3, id_usuario: 2, id_especie: 1, nome: 'Tanque Leste', volume_litros: 300, quantidade_peixes: 30, data_povoamento: '2026-08-24', status: 'ativo', criado_em: criadoEm },
    { id: 4, id_usuario: 1, id_especie: 1, nome: 'Tanque Oeste', volume_litros: 250, quantidade_peixes: 0, data_povoamento: null, status: 'manutencao', criado_em: criadoEm },
    { id: 5, id_usuario: 1, id_especie: 1, nome: 'Tanque Berçário', volume_litros: 80, quantidade_peixes: 15, data_povoamento: '2026-09-28', status: 'ativo', criado_em: criadoEm },
  ]

  const dispositivos: DispositivoSimulado[] = [1, 2, 3, 4].map((n) => ({
    id: n,
    id_tanque: n,
    nome: `Nó sensor ${tanques[n - 1]!.nome.replace('Tanque ', '')}`,
    modelo_esp32: 'ESP32 DevKitC V4',
    mac_address: `a4:f0:0f:64:3c:${(0x6f + n).toString(16)}`,
    versao_firmware: '1.2.0',
    ip_local: `192.168.0.${20 + n}`,
    data_cadastro: criadoEm,
    cenario: n - 1,
    sem_dados_desde: n === 4 ? agora - 7 * MINUTO : null,
    falhas: n === 1 ? { turbidez: agora - 12 * MINUTO } : {},
  }))

  const sensores: SensorSimulado[] = dispositivos.flatMap((d) =>
    TIPOS_SENSOR.map((tipo) => ({
      id: (d.id - 1) * TIPOS_SENSOR.length + tipo.id,
      id_dispositivo: d.id,
      id_tipo: tipo.id,
      id_tanque: d.id_tanque,
      data_instalacao: dataInstalacao,
      status: 'ativo' as StatusSensor,
    })),
  )

  return { tanques, dispositivos, sensores }
}
