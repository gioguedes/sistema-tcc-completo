import { respostaToken, usuario } from '@/dominio/entidades'
import { requisitar } from './cliente'
import { sessao } from './sessao'

export async function entrar(dados: { email: string; senha: string; lembrar: boolean }) {
  const resposta = await requisitar('/auth/login', respostaToken, { metodo: 'POST', corpo: dados, publica: true })
  sessao.definirToken(resposta.access_token)
}

export async function sair() {
  try {
    await requisitar('/auth/logout', null, { metodo: 'POST' })
  } finally {
    sessao.definirToken(null)
  }
}

export const buscarUsuarioAtual = (sinal?: AbortSignal) => requisitar('/auth/eu', usuario, { sinal })

export const atualizarConta = (dados: { nome: string; telefone: string | null }) =>
  requisitar('/auth/eu', usuario, { metodo: 'PATCH', corpo: dados })
