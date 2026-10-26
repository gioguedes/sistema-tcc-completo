import { useSyncExternalStore } from 'react'
import { QueryCache, QueryClient, type Query } from '@tanstack/react-query'
import type { Tanque } from '@/dominio/entidades'
import { ErroApi, type TipoErro } from '@/infra/api/erros'
import { sessao } from '@/infra/api/sessao'
import { salvarUltimaLeitura } from '@/infra/armazenamento/ultimaLeitura'
import { chaves } from './chaves'

/**
 * Enquanto o WebSocket (Socket.IO) não existe no backend, os dados "ao vivo" são
 * atualizados por sondagem — o mesmo modo de contingência previsto no TC2 (§14).
 * As leituras chegam a cada 60 s (RF01), então 30 s mantém a tela no máximo meio ciclo atrasada.
 */
export const INTERVALO_ATUALIZACAO_MS = 30_000

let ultimaAtualizacao: number | null = null
const ouvintes = new Set<() => void>()

function registrarAtualizacao() {
  ultimaAtualizacao = Date.now()
  ouvintes.forEach((ouvinte) => ouvinte())
}

/** Momento do último dado recebido com sucesso da API (cartão "Conectado — Última atualização"). */
export function useUltimaAtualizacao(): number | null {
  return useSyncExternalStore(
    (aoMudar) => {
      ouvintes.add(aoMudar)
      return () => ouvintes.delete(aoMudar)
    },
    () => ultimaAtualizacao,
  )
}

const ERROS_SEM_NOVA_TENTATIVA: TipoErro[] = [
  'nao_encontrado',
  'proibido',
  'sessao_expirada',
  'credenciais',
  'validacao',
  'indisponivel',
  'resposta_invalida',
]

/** Cada lista de tanques recebida vira a "última leitura" que o painel mostra quando abre sem rede. */
function aoReceber(dados: unknown, consulta: Query<unknown, unknown, unknown>) {
  registrarAtualizacao()
  const ehListaDeTanques = consulta.queryKey.length === 1 && consulta.queryKey[0] === chaves.tanques[0]
  // sem token, a resposta chegou depois do "Sair" e não deve ser guardada
  if (ehListaDeTanques && sessao.token()) void salvarUltimaLeitura(dados as Tanque[])
}

export function criarClienteQuery() {
  return new QueryClient({
    queryCache: new QueryCache({ onSuccess: aoReceber }),
    defaultOptions: {
      queries: {
        staleTime: 20_000,
        retry: (falhas, erro) =>
          falhas < 2 && !(erro instanceof ErroApi && ERROS_SEM_NOVA_TENTATIVA.includes(erro.tipo)),
      },
      mutations: { retry: false },
    },
  })
}
