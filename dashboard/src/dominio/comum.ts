import { z } from 'zod'

/**
 * Colunas NUMERIC do PostgreSQL chegam do FastAPI/Pydantic como string ("6.50") por padrão.
 * Aceitamos número ou string numérica e entregamos sempre `number`.
 */
export const numero = z.union([z.number(), z.string()]).transform((valor, ctx) => {
  const convertido = typeof valor === 'number' ? valor : Number(valor)
  if (!Number.isFinite(convertido)) {
    ctx.addIssue({ code: 'custom', message: 'Número inválido' })
    return z.NEVER
  }
  return convertido
})

export const id = z.number().int()
export const dataHora = z.string()

// Domínios espelham as restrições CHECK do Apêndice A (01_apendice_a_ddl.sql).
export const nivelRisco = z.enum(['otimo', 'atencao', 'critico'])
export const grandeza = z.enum(['ph', 'temperatura', 'turbidez', 'od'])
export const perfil = z.enum(['admin', 'operador'])
export const statusTanque = z.enum(['ativo', 'manutencao', 'inativo'])
export const statusConexao = z.enum(['online', 'offline'])
export const statusSensor = z.enum(['ativo', 'inativo', 'em_calibracao'])
export const canalAlerta = z.enum(['whatsapp', 'email', 'sms'])
export const statusAlerta = z.enum(['pendente', 'enviado', 'falha'])
export const acaoAtuador = z.enum(['ligar', 'desligar'])

export type NivelRisco = z.infer<typeof nivelRisco>
export type Grandeza = z.infer<typeof grandeza>
export type Perfil = z.infer<typeof perfil>
export type StatusTanque = z.infer<typeof statusTanque>
export type StatusConexao = z.infer<typeof statusConexao>
export type StatusSensor = z.infer<typeof statusSensor>
export type CanalAlerta = z.infer<typeof canalAlerta>
export type StatusAlerta = z.infer<typeof statusAlerta>
export type AcaoAtuador = z.infer<typeof acaoAtuador>

export function paginado<T extends z.ZodType>(item: T) {
  return z.object({
    itens: z.array(item),
    total: z.number().int(),
    pagina: z.number().int(),
    por_pagina: z.number().int(),
  })
}
