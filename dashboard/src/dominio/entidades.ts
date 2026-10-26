import { z } from 'zod'
import {
  acaoAtuador,
  canalAlerta,
  dataHora,
  grandeza,
  id,
  nivelRisco,
  numero,
  paginado,
  perfil,
  statusAlerta,
  statusConexao,
  statusSensor,
  statusTanque,
} from './comum'

export const usuario = z.object({
  id,
  nome: z.string(),
  email: z.string(),
  telefone: z.string().nullable(),
  perfil,
})

export const respostaToken = z.object({
  access_token: z.string().min(1),
  expira_em: dataHora,
})

export const especie = z.object({
  id,
  nome_comum: z.string(),
  nome_cientifico: z.string(),
  ph_min: numero,
  ph_max: numero,
  temp_min: numero,
  temp_max: numero,
  od_min: numero,
  od_max: numero,
})

export const leituraAtual = z.object({
  grandeza,
  valor: numero,
  unidade: z.string(),
  ts: dataHora,
  estimado: z.boolean().default(false),
  /** Só no OD estimado: confiança abaixo do mínimo do serviço de ML (UC06, fluxo alternativo). */
  baixa_confianca: z.boolean().default(false),
})

export const resumoDispositivo = z.object({
  id,
  nome: z.string(),
  status_conexao: statusConexao,
  ultima_leitura_em: dataHora.nullable(),
})

export const tanque = z.object({
  id,
  nome: z.string(),
  volume_litros: numero,
  quantidade_peixes: z.number().int(),
  data_povoamento: z.string().nullable(),
  status: statusTanque,
  criado_em: dataHora,
  especie: especie.nullable(),
  nivel_risco: nivelRisco.nullable(),
  ultima_leitura_em: dataHora.nullable(),
  ultimas_leituras: z.array(leituraAtual),
  dispositivos: z.array(resumoDispositivo),
})

export const sensor = z.object({
  id,
  grandeza,
  modelo: z.string(),
  unidade: z.string(),
  status: statusSensor,
  data_instalacao: z.string(),
})

export const acionamento = z.object({
  id,
  acao: acaoAtuador,
  motivo: z.string().nullable(),
  ts_acionamento: dataHora,
})

/** Último comando do aerador do dispositivo; o nó ainda não confirma o estado do relé. */
export const ultimoAcionamento = acionamento.extend({ automatico: z.boolean() })

export const dispositivo = z.object({
  id,
  id_tanque: id,
  nome: z.string(),
  modelo_esp32: z.string(),
  mac_address: z.string(),
  versao_firmware: z.string().nullable(),
  ip_local: z.string().nullable(),
  status_conexao: statusConexao,
  ultima_leitura_em: dataHora.nullable(),
  data_cadastro: dataHora,
  sensores: z.array(sensor),
  ultimo_acionamento: ultimoAcionamento.nullable().default(null),
})

export const bucket = z.enum(['raw', '5m', '1h'])

export const pontoSerie = z.object({
  ts: dataHora,
  valor: numero,
  min: numero.optional(),
  max: numero.optional(),
})

export const serieLeituras = z.object({
  grandeza,
  unidade: z.string(),
  estimado: z.boolean().default(false),
  pontos: z.array(pontoSerie),
})

export const respostaLeituras = z.object({
  id_tanque: id,
  bucket,
  desde: dataHora,
  ate: dataHora,
  series: z.array(serieLeituras),
})

export const previsao = z.object({
  id,
  parametro_critico: grandeza,
  valor_previsto: numero,
  nivel_risco: nivelRisco,
  horizonte_h: z.number().int().min(1).max(3),
  confianca: numero.nullable(),
  baixa_confianca: z.boolean().default(false),
  ts_previsao: dataHora,
})

/** Linha `horizonte_h = 0` de `previsoes`: OD estimado no instante do ciclo do serviço de ML. */
export const estimativaOd = z.object({
  valor: numero,
  nivel_risco: nivelRisco,
  confianca: numero.nullable(),
  baixa_confianca: z.boolean().default(false),
})

export const previsaoAtual = z.object({
  id_tanque: id,
  nivel_risco: nivelRisco.nullable(),
  gerada_em: dataHora.nullable(),
  od_atual: estimativaOd.nullable().default(null),
  horizontes: z.array(previsao),
})

export const alerta = z.object({
  id,
  id_tanque: id,
  tanque_nome: z.string(),
  id_previsao: id.nullable(),
  mensagem: z.string(),
  recomendacoes: z.array(z.string()).default([]),
  nivel_risco: nivelRisco.nullable(),
  parametro: grandeza.nullable(),
  canal: canalAlerta,
  status: statusAlerta,
  ts_envio: dataHora.nullable(),
  criado_em: dataHora,
})

const baseEvento = { id: z.string(), id_tanque: id, tanque_nome: z.string(), ocorrido_em: dataHora }

export const evento = z.discriminatedUnion('tipo', [
  z.object({ ...baseEvento, tipo: z.literal('alerta'), nivel_risco: nivelRisco.nullable(), mensagem: z.string() }),
  z.object({
    ...baseEvento,
    tipo: z.literal('acionamento'),
    acao: acaoAtuador,
    automatico: z.boolean(),
    motivo: z.string().nullable(),
  }),
])

export const alertasPaginados = paginado(alerta)
export const eventosPaginados = paginado(evento)

export type Usuario = z.infer<typeof usuario>
export type Especie = z.infer<typeof especie>
export type LeituraAtual = z.infer<typeof leituraAtual>
export type ResumoDispositivo = z.infer<typeof resumoDispositivo>
export type Tanque = z.infer<typeof tanque>
export type Sensor = z.infer<typeof sensor>
export type Dispositivo = z.infer<typeof dispositivo>
export type Bucket = z.infer<typeof bucket>
export type PontoSerie = z.infer<typeof pontoSerie>
export type SerieLeituras = z.infer<typeof serieLeituras>
export type RespostaLeituras = z.infer<typeof respostaLeituras>
export type Previsao = z.infer<typeof previsao>
export type EstimativaOd = z.infer<typeof estimativaOd>
export type PrevisaoAtual = z.infer<typeof previsaoAtual>
export type Alerta = z.infer<typeof alerta>
export type Evento = z.infer<typeof evento>
export type Acionamento = z.infer<typeof acionamento>
export type UltimoAcionamento = z.infer<typeof ultimoAcionamento>
