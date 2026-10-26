import { keepPreviousData, useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AcaoAtuador } from '@/dominio/comum'
import { chaveDoPeriodo, escolherBucket, resolverPeriodo, type Periodo } from '@/compartilhado/periodo'
import {
  buscarLeituras,
  buscarPrevisaoAtual,
  comandarAerador,
  listarAlertas,
  listarEventos,
  type FiltroAlertas,
} from '@/infra/api/recursos'
import { chaves } from './chaves'
import { INTERVALO_ATUALIZACAO_MS } from './cliente'

export function useLeituras(idTanque: number, periodo: Periodo) {
  return useQuery({
    queryKey: chaves.leituras(idTanque, chaveDoPeriodo(periodo)),
    queryFn: ({ signal }) => {
      // A janela é calculada na hora da busca, para períodos relativos acompanharem o relógio.
      const { desde, ate } = resolverPeriodo(periodo)
      return buscarLeituras(idTanque, { desde, ate, bucket: escolherBucket(desde, ate) }, signal)
    },
    enabled: Number.isInteger(idTanque) && idTanque > 0,
    refetchInterval: periodo.tipo === 'relativo' ? INTERVALO_ATUALIZACAO_MS : false,
    placeholderData: keepPreviousData,
  })
}

const opcoesPrevisao = (idTanque: number) => ({
  queryKey: chaves.previsaoAtual(idTanque),
  queryFn: ({ signal }: { signal: AbortSignal }) => buscarPrevisaoAtual(idTanque, signal),
  refetchInterval: INTERVALO_ATUALIZACAO_MS,
})

export function usePrevisaoAtual(idTanque: number) {
  return useQuery({ ...opcoesPrevisao(idTanque), enabled: Number.isInteger(idTanque) && idTanque > 0 })
}

export function usePrevisoesAtuais(idsTanques: number[]) {
  return useQueries({ queries: idsTanques.map(opcoesPrevisao) })
}

export function useAlertas(filtro: FiltroAlertas) {
  return useQuery({
    queryKey: chaves.listaAlertas(filtro),
    queryFn: ({ signal }) => listarAlertas(filtro, signal),
    refetchInterval: INTERVALO_ATUALIZACAO_MS,
    placeholderData: keepPreviousData,
  })
}

/** Alertas que ainda pedem ação (a regra de "ativo" é do backend). Alimenta o contador do menu. */
export function useAlertasAtivos() {
  return useAlertas({ ativos: true, porPagina: 20 })
}

export function useEventos(pagina: number, porPagina: number) {
  return useQuery({
    queryKey: chaves.listaEventos(pagina, porPagina),
    queryFn: ({ signal }) => listarEventos(pagina, porPagina, signal),
    refetchInterval: INTERVALO_ATUALIZACAO_MS,
    placeholderData: keepPreviousData,
  })
}

export function useComandarAerador() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ idDispositivo, acao }: { idDispositivo: number; acao: AcaoAtuador }) =>
      comandarAerador(idDispositivo, acao),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: chaves.eventos })
      // o último comando do aerador aparece na lista de dispositivos do tanque
      void queryClient.invalidateQueries({ queryKey: chaves.tanques, predicate: (q) => q.queryKey[2] === 'dispositivos' })
    },
  })
}
