import { respostaToken } from '@/dominio/entidades'
import { montarUrl, TEMPO_LIMITE_MS } from './url'

/**
 * Token de acesso mantido apenas em memória (RNF05): nunca vai para localStorage.
 * A renovação usa o cookie HttpOnly emitido pela API, que o front-end não consegue ler.
 */
let tokenAcesso: string | null = null
let renovacaoEmAndamento: Promise<ResultadoRenovacao> | null = null
const ouvintesExpiracao = new Set<() => void>()

/**
 * "sem_sessao": o servidor recusou o cookie (401/403), é preciso entrar de novo.
 * "sem_conexao": rede, tempo esgotado ou servidor fora do ar — a sessão pode continuar válida.
 */
export type ResultadoRenovacao = 'renovada' | 'sem_sessao' | 'sem_conexao'

async function pedirRenovacao(): Promise<ResultadoRenovacao> {
  try {
    const resposta = await fetch(montarUrl('/auth/refresh'), {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(TEMPO_LIMITE_MS),
    })
    if (resposta.status === 401 || resposta.status === 403) return 'sem_sessao'
    if (!resposta.ok) return 'sem_conexao'
    const dados = respostaToken.safeParse(await resposta.json())
    if (!dados.success) return 'sem_sessao'
    tokenAcesso = dados.data.access_token
    return 'renovada'
  } catch {
    return 'sem_conexao'
  }
}

export const sessao = {
  token: () => tokenAcesso,

  definirToken(token: string | null) {
    tokenAcesso = token
  },

  /** Requisições concorrentes que recebem 401 aguardam a mesma renovação. */
  async renovar(): Promise<boolean> {
    return (await sessao.restaurar()) === 'renovada'
  },

  /** Como `renovar`, mas diz por que falhou: ao abrir o app sem rede, o painel mostra a última leitura salva. */
  restaurar(): Promise<ResultadoRenovacao> {
    renovacaoEmAndamento ??= pedirRenovacao().finally(() => {
      renovacaoEmAndamento = null
    })
    return renovacaoEmAndamento
  },

  expirar() {
    tokenAcesso = null
    ouvintesExpiracao.forEach((ouvinte) => ouvinte())
  },

  aoExpirar(ouvinte: () => void) {
    ouvintesExpiracao.add(ouvinte)
    return () => {
      ouvintesExpiracao.delete(ouvinte)
    }
  },
}
