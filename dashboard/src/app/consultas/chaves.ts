import type { FiltroAlertas } from '@/infra/api/recursos'

/** Chaves de cache padronizadas: permitem invalidar só o que mudou. */
export const chaves = {
  especies: ['especies'] as const,
  tanques: ['tanques'] as const,
  tanque: (id: number) => ['tanques', id] as const,
  dispositivos: (id: number) => ['tanques', id, 'dispositivos'] as const,
  leituras: (id: number, periodo: string) => ['tanques', id, 'leituras', periodo] as const,
  previsaoAtual: (id: number) => ['tanques', id, 'previsao-atual'] as const,
  alertas: ['alertas'] as const,
  listaAlertas: (filtro: FiltroAlertas) => ['alertas', filtro] as const,
  eventos: ['eventos'] as const,
  listaEventos: (pagina: number, porPagina: number) => ['eventos', pagina, porPagina] as const,
}
