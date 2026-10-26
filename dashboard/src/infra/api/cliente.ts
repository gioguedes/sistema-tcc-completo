import type { z } from 'zod'
import { ErroApi, erroDeResposta } from './erros'
import { sessao } from './sessao'
import { montarUrl, TEMPO_LIMITE_MS, type Parametros } from './url'

type Metodo = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export interface OpcoesRequisicao {
  metodo?: Metodo
  corpo?: unknown
  parametros?: Parametros
  sinal?: AbortSignal
  /** Rotas públicas (login) não enviam token nem tentam renovar a sessão. */
  publica?: boolean
}

async function executar(caminho: string, opcoes: OpcoesRequisicao, token: string | null): Promise<Response> {
  const tempoLimite = AbortSignal.timeout(TEMPO_LIMITE_MS)
  const sinal = opcoes.sinal ? AbortSignal.any([opcoes.sinal, tempoLimite]) : tempoLimite
  const cabecalhos: Record<string, string> = { Accept: 'application/json' }
  if (opcoes.corpo !== undefined) cabecalhos['Content-Type'] = 'application/json'
  if (token) cabecalhos.Authorization = `Bearer ${token}`

  try {
    return await fetch(montarUrl(caminho, opcoes.parametros), {
      method: opcoes.metodo ?? 'GET',
      headers: cabecalhos,
      body: opcoes.corpo === undefined ? undefined : JSON.stringify(opcoes.corpo),
      credentials: 'include',
      signal: sinal,
    })
  } catch (erro) {
    // Cancelamento pedido pelo chamador (ex.: TanStack Query ao trocar de tela) não é falha de rede.
    if (opcoes.sinal?.aborted) throw erro
    if (tempoLimite.aborted) throw new ErroApi('timeout')
    throw new ErroApi('rede')
  }
}

/**
 * Faz a requisição, renova a sessão uma única vez em caso de 401 e valida
 * a resposta com o esquema Zod do domínio antes de entregá-la à interface.
 */
export async function requisitar<E extends z.ZodType>(
  caminho: string,
  esquema: E | null,
  opcoes: OpcoesRequisicao = {},
): Promise<z.output<E>> {
  const autenticada = !opcoes.publica
  let resposta = await executar(caminho, opcoes, autenticada ? sessao.token() : null)

  if (resposta.status === 401 && autenticada) {
    const renovada = await sessao.renovar()
    if (renovada) resposta = await executar(caminho, opcoes, sessao.token())
    if (!renovada || resposta.status === 401) {
      sessao.expirar()
      throw new ErroApi('sessao_expirada', 401)
    }
  }

  if (!resposta.ok) throw await erroDeResposta(resposta)
  if (resposta.status === 204 || esquema === null) return undefined as z.output<E>

  let corpo: unknown
  try {
    corpo = await resposta.json()
  } catch {
    throw new ErroApi('resposta_invalida', resposta.status)
  }

  const resultado = esquema.safeParse(corpo)
  if (!resultado.success) {
    if (import.meta.env.DEV) console.error(`Resposta fora do contrato em ${caminho}`, resultado.error.issues)
    throw new ErroApi('resposta_invalida', resposta.status)
  }
  return resultado.data
}
