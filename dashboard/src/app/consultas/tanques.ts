import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { StatusSensor } from '@/dominio/comum'
import type { Tanque } from '@/dominio/entidades'
import {
  atualizarDispositivo,
  atualizarSensor,
  atualizarTanque,
  buscarTanque,
  criarDispositivo,
  criarTanque,
  listarDispositivosDoTanque,
  listarEspecies,
  listarTanques,
  type DadosDispositivo,
  type DadosTanque,
} from '@/infra/api/recursos'
import { chaves } from './chaves'
import { INTERVALO_ATUALIZACAO_MS } from './cliente'

export function useEspecies() {
  return useQuery({
    queryKey: chaves.especies,
    queryFn: ({ signal }) => listarEspecies(signal),
    staleTime: 60 * 60_000,
  })
}

export function useTanques() {
  return useQuery({
    queryKey: chaves.tanques,
    queryFn: ({ signal }) => listarTanques(signal),
    refetchInterval: INTERVALO_ATUALIZACAO_MS,
  })
}

export function useTanque(id: number) {
  const queryClient = useQueryClient()
  return useQuery<Tanque>({
    queryKey: chaves.tanque(id),
    queryFn: ({ signal }) => buscarTanque(id, signal),
    refetchInterval: INTERVALO_ATUALIZACAO_MS,
    enabled: Number.isInteger(id) && id > 0,
    // Vindo da lista, o tanque aparece na hora enquanto o detalhe é revalidado.
    placeholderData: () => queryClient.getQueryData<Tanque[]>(chaves.tanques)?.find((t) => t.id === id),
  })
}

export function useDispositivos(idTanque: number) {
  return useQuery({
    queryKey: chaves.dispositivos(idTanque),
    queryFn: ({ signal }) => listarDispositivosDoTanque(idTanque, signal),
    refetchInterval: INTERVALO_ATUALIZACAO_MS,
    enabled: Number.isInteger(idTanque) && idTanque > 0,
  })
}

export function useCriarTanque() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: criarTanque,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chaves.tanques }),
  })
}

export function useAtualizarTanque(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (dados: DadosTanque) => atualizarTanque(id, dados),
    onSuccess: (tanque) => {
      queryClient.setQueryData(chaves.tanque(id), tanque)
      return queryClient.invalidateQueries({ queryKey: chaves.tanques })
    },
  })
}

export function useCriarDispositivo(idTanque: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (dados: DadosDispositivo) => criarDispositivo({ ...dados, id_tanque: idTanque }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chaves.tanques }),
  })
}

export function useAtualizarDispositivo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: DadosDispositivo }) => atualizarDispositivo(id, dados),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chaves.tanques }),
  })
}

export function useAtualizarSensor(idTanque: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: StatusSensor }) => atualizarSensor(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chaves.dispositivos(idTanque) }),
  })
}
