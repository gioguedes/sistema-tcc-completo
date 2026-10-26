import { useState, useSyncExternalStore } from 'react'

/**
 * O service worker só existe no build sem dados simulados (o MSW ocupa o mesmo escopo).
 * Sem ele não há abertura offline, então o convite de instalação também não aparece.
 */
export const PWA_ATIVO = import.meta.env.PROD && import.meta.env.VITE_USAR_MOCKS !== 'true'

/** Evento do Chrome, Edge e Android que deixa o app abrir o pedido de instalação na hora que escolher. */
interface EventoInstalacao extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

/**
 * - instalado: o painel já está aberto como aplicativo;
 * - disponivel: o navegador entregou o evento de instalação;
 * - ios: iPhone e iPad não têm o evento; a instalação é por Compartilhar > Adicionar à Tela de Início;
 * - indisponivel: navegador sem instalação, ou o pedido já foi usado nesta visita.
 */
export type SituacaoInstalacao = 'instalado' | 'disponivel' | 'ios' | 'indisponivel'

interface RegistroInstalacao {
  visitas: number
  conviteDispensado: boolean
}

const CHAVE = 'painel-aquicola:instalacao'
const REGISTRO_PADRAO: RegistroInstalacao = { visitas: 0, conviteDispensado: false }

let eventoGuardado: EventoInstalacao | null = null
let instalado = false
const ouvintes = new Set<() => void>()
const avisar = () => ouvintes.forEach((ouvinte) => ouvinte())

function lerRegistro(): RegistroInstalacao {
  try {
    const salvo = localStorage.getItem(CHAVE)
    return salvo ? { ...REGISTRO_PADRAO, ...(JSON.parse(salvo) as Partial<RegistroInstalacao>) } : REGISTRO_PADRAO
  } catch {
    return REGISTRO_PADRAO
  }
}

function salvarRegistro(registro: RegistroInstalacao) {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(registro))
  } catch {
    // aba anônima: o convite só não lembra que foi dispensado
  }
}

function abertoComoAplicativo(): boolean {
  const iosStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true
  return iosStandalone || (window.matchMedia?.('(display-mode: standalone)').matches ?? false)
}

function ehIos(): boolean {
  // o iPadOS se apresenta como Mac; o toque denuncia
  return /iphone|ipad|ipod/i.test(navigator.userAgent) || (/macintosh/i.test(navigator.userAgent) && navigator.maxTouchPoints > 1)
}

/** Chamado uma vez em main.tsx, antes do React: o evento pode chegar antes de qualquer tela montar. */
export function iniciarInstalacao() {
  const registro = lerRegistro()
  salvarRegistro({ ...registro, visitas: registro.visitas + 1 })
  instalado = abertoComoAplicativo()
  window.addEventListener('beforeinstallprompt', (evento) => {
    // sem a barra automática do navegador: o convite aparece no momento certo (TC2 §9)
    evento.preventDefault()
    eventoGuardado = evento as EventoInstalacao
    avisar()
  })
  window.addEventListener('appinstalled', () => {
    eventoGuardado = null
    instalado = true
    avisar()
  })
}

function situacaoAtual(): SituacaoInstalacao {
  if (instalado) return 'instalado'
  if (eventoGuardado) return 'disponivel'
  return ehIos() ? 'ios' : 'indisponivel'
}

function assinar(aoMudar: () => void) {
  ouvintes.add(aoMudar)
  return () => {
    ouvintes.delete(aoMudar)
  }
}

export function useSituacaoInstalacao(): SituacaoInstalacao {
  return useSyncExternalStore(assinar, situacaoAtual)
}

/** Abre o pedido do navegador. O evento só pode ser usado uma vez. */
export async function instalarAplicativo(): Promise<boolean> {
  const evento = eventoGuardado
  if (!evento) return false
  eventoGuardado = null
  avisar()
  await evento.prompt()
  const { outcome } = await evento.userChoice
  return outcome === 'accepted'
}

/** "Não na primeira visita" (TC2 §9): o convite aparece a partir da segunda abertura, até ser dispensado. */
export function useConviteInstalacao() {
  const situacao = useSituacaoInstalacao()
  const [registro, setRegistro] = useState(lerRegistro)
  const dispensar = () => {
    const novo = { ...registro, conviteDispensado: true }
    salvarRegistro(novo)
    setRegistro(novo)
  }
  const mostrar = (situacao === 'disponivel' || situacao === 'ios') && registro.visitas >= 2 && !registro.conviteDispensado
  return { mostrar, situacao, dispensar }
}
