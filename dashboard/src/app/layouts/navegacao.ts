import { Bell, CalendarClock, FileText, Fish, History, House, Settings, SlidersHorizontal, TrendingUp, type LucideIcon } from 'lucide-react'

export interface ItemNavegacao {
  para: string
  rotulo: string
  icone: LucideIcon
  /** Mostra o contador de alertas ativos. */
  contadorAlertas?: boolean
  /** Outras rotas que também marcam o item como ativo. */
  ativoEm?: (caminho: string) => boolean
}

/** Barra lateral do Figma (desktop). */
export const MENU_LATERAL: ItemNavegacao[] = [
  { para: '/', rotulo: 'Início', icone: House, ativoEm: (c) => c === '/' },
  { para: '/tanques', rotulo: 'Tanques', icone: Fish, ativoEm: (c) => c.startsWith('/tanques') },
  { para: '/historico', rotulo: 'Histórico', icone: History },
  { para: '/previsao', rotulo: 'Previsão', icone: TrendingUp },
  { para: '/alertas', rotulo: 'Alertas', icone: Bell, contadorAlertas: true },
  { para: '/eventos', rotulo: 'Eventos', icone: CalendarClock },
  { para: '/relatorios', rotulo: 'Relatórios', icone: FileText },
  { para: '/configuracoes', rotulo: 'Configurações', icone: Settings },
]

/** Barra inferior do Figma (celular). "Tanques" é a visão geral. */
export const MENU_INFERIOR: ItemNavegacao[] = [
  { para: '/', rotulo: 'Tanques', icone: Fish, ativoEm: (c) => c === '/' || c.startsWith('/tanques') },
  { para: '/historico', rotulo: 'Histórico', icone: History, ativoEm: (c) => c.startsWith('/historico') || c.startsWith('/relatorios') },
  { para: '/alertas', rotulo: 'Alertas', icone: Bell, contadorAlertas: true, ativoEm: (c) => c.startsWith('/alertas') || c.startsWith('/eventos') || c.startsWith('/previsao') },
  { para: '/configuracoes', rotulo: 'Ajustes', icone: SlidersHorizontal },
]

export function itemAtivo(item: ItemNavegacao, caminho: string): boolean {
  return item.ativoEm ? item.ativoEm(caminho) : caminho.startsWith(item.para)
}
