import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { buscarConfigAlertas, salvarConfigAlertas } from '@/infra/api/recursos'
import { chaves } from './chaves'

export function useConfigAlertas() {
  return useQuery({
    queryKey: chaves.configAlertas,
    queryFn: ({ signal }) => buscarConfigAlertas(signal),
  })
}

export function useSalvarConfigAlertas() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: salvarConfigAlertas,
    onSuccess: (dados) => cliente.setQueryData(chaves.configAlertas, dados),
  })
}
