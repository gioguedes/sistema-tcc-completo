import { setupWorker } from 'msw/browser'
import { defineNetwork, InterceptorSource } from 'msw/experimental'
import { FetchInterceptor } from '@mswjs/interceptors/fetch'
import { resetarBanco } from './banco'
import { handlers } from './handlers'

const worker = setupWorker(...handlers)

export async function iniciarServidorSimulado() {
  try {
    await worker.start({ onUnhandledFrame: 'bypass', quiet: true })
  } catch (erro) {
    // Alguns navegadores embutidos bloqueiam Service Workers: intercepta o fetch na própria página.
    console.warn('[Painel Aquícola] Service Worker indisponível; dados simulados em modo de compatibilidade.', erro)
    const rede = defineNetwork({
      sources: [new InterceptorSource({ interceptors: [new FetchInterceptor()] })],
      handlers,
      onUnhandledFrame: 'bypass',
      context: { quiet: true },
    })
    await rede.enable()
  }
}

// Atalho para apresentações: `painelAquicola.restaurarDadosSimulados()` no console do navegador.
Object.assign(window, { painelAquicola: { restaurarDadosSimulados: resetarBanco } })
