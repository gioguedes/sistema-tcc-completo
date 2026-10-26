import { flushSync } from 'react-dom'
import type { Tema } from '@/infra/armazenamento/preferencias'

const COR_BARRA: Record<'claro' | 'escuro', string> = { claro: '#2f6f73', escuro: '#0f191a' }

function sistemaEscuro() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

export function temaEfetivo(tema: Tema): 'claro' | 'escuro' {
  if (tema !== 'automatico') return tema
  return sistemaEscuro() ? 'escuro' : 'claro'
}

/** Os tokens do index.css trocam pelo atributo data-tema do <html>. */
export function aplicarTema(tema: Tema) {
  const efetivo = temaEfetivo(tema)
  document.documentElement.dataset.tema = efetivo
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', COR_BARRA[efetivo])
}

/**
 * Troca o tema com o círculo que se abre a partir do ponto tocado (referência: Skiper UI 26),
 * usando a View Transition API do navegador. Sem suporte ou com "reduzir movimento", troca na hora.
 */
export function trocarTemaComTransicao(atualizar: () => void, origem?: { x: number; y: number }) {
  const reduzir = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduzir || typeof document.startViewTransition !== 'function') {
    atualizar()
    return
  }
  const x = origem?.x ?? window.innerWidth / 2
  const y = origem?.y ?? window.innerHeight / 2
  const raio = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y))
  const transicao = document.startViewTransition(() => flushSync(atualizar))
  void transicao.ready.then(() => {
    document.documentElement.animate(
      { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${raio}px at ${x}px ${y}px)`] },
      // 400 ms: a mesma duração que o TC2 (§8.3) usa para a mudança de estado do veredito
      { duration: 400, easing: 'ease-out', pseudoElement: '::view-transition-new(root)' },
    )
  })
}

/**
 * Mantém o tema em dia: acompanha o sistema no modo "Automático" e imprime sempre no claro
 * (relatório em papel com texto claro ficaria ilegível). Devolve a função de limpeza.
 */
export function observarTema(tema: Tema) {
  aplicarTema(tema)
  const consulta = window.matchMedia?.('(prefers-color-scheme: dark)')
  const aoMudarSistema = () => tema === 'automatico' && aplicarTema(tema)
  const antesDeImprimir = () => {
    document.documentElement.dataset.tema = 'claro'
  }
  const depoisDeImprimir = () => aplicarTema(tema)
  consulta?.addEventListener('change', aoMudarSistema)
  window.addEventListener('beforeprint', antesDeImprimir)
  window.addEventListener('afterprint', depoisDeImprimir)
  return () => {
    consulta?.removeEventListener('change', aoMudarSistema)
    window.removeEventListener('beforeprint', antesDeImprimir)
    window.removeEventListener('afterprint', depoisDeImprimir)
  }
}
