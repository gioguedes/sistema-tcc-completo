import { useEffect, useState, useSyncExternalStore } from 'react'

/** Relógio que avança a cada `intervaloMs`, para textos como "há 3 min" se atualizarem sozinhos. */
export function useAgora(intervaloMs = 30_000): number {
  const [agora, setAgora] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setAgora(Date.now()), intervaloMs)
    return () => window.clearInterval(id)
  }, [intervaloMs])
  return agora
}

function assinarConexao(aoMudar: () => void) {
  window.addEventListener('online', aoMudar)
  window.addEventListener('offline', aoMudar)
  return () => {
    window.removeEventListener('online', aoMudar)
    window.removeEventListener('offline', aoMudar)
  }
}

/** Conexão do navegador — diferente do nó sensor offline (TC2, princípio 3). */
export function useOnline(): boolean {
  return useSyncExternalStore(assinarConexao, () => navigator.onLine)
}

export function useTituloDocumento(titulo: string) {
  useEffect(() => {
    document.title = titulo ? `${titulo} · Painel Aquícola` : 'Painel Aquícola'
  }, [titulo])
}
