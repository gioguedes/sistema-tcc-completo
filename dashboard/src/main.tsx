import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/public-sans'
import './index.css'
import { App } from './app/App'
import { iniciarInstalacao } from './app/instalacao'
import { aplicarTema } from './app/tema'
import { lerPreferencias } from './infra/armazenamento/preferencias'

// antes do primeiro desenho, para não piscar o tema errado
aplicarTema(lerPreferencias().tema)
// o navegador pode oferecer a instalação antes de qualquer tela montar
iniciarInstalacao()

/**
 * Com VITE_USAR_MOCKS=true, o servidor simulado (MSW) responde às chamadas de /api/v1
 * até o backend FastAPI existir. Com "false", nada do mock entra no bundle.
 */
async function iniciarDadosSimulados() {
  if (import.meta.env.VITE_USAR_MOCKS !== 'true') return
  const { iniciarServidorSimulado } = await import('./mocks/navegador')
  await iniciarServidorSimulado()
}

iniciarDadosSimulados().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
