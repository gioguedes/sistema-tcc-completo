import { lazy, Suspense, useState } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router'
import { ProvedorToast } from '@/ui/Toast'
import { criarClienteQuery } from './consultas/cliente'
import { ProvedorAutenticacao } from './funcionalidades/autenticacao/ProvedorAutenticacao'
import { PWA_ATIVO } from './instalacao'
import { ProvedorPreferencias } from './preferencias'
import { roteador } from './rotas'

// só no build sem dados simulados: registra o service worker e avisa das versões novas
const AvisoAtualizacao = lazy(() => import('./componentes/AvisoAtualizacao'))

export function App() {
  const [clienteQuery] = useState(criarClienteQuery)
  return (
    <QueryClientProvider client={clienteQuery}>
      <ProvedorPreferencias>
        <ProvedorToast>
          <ProvedorAutenticacao>
            <RouterProvider router={roteador} />
          </ProvedorAutenticacao>
          {PWA_ATIVO && (
            <Suspense fallback={null}>
              <AvisoAtualizacao />
            </Suspense>
          )}
        </ProvedorToast>
      </ProvedorPreferencias>
    </QueryClientProvider>
  )
}
