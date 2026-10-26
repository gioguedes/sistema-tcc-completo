import { render } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router'
import { criarClienteQuery } from '@/app/consultas/cliente'
import { ProvedorAutenticacao } from '@/app/funcionalidades/autenticacao/ProvedorAutenticacao'
import { ProvedorPreferencias } from '@/app/preferencias'
import { ProvedorToast } from '@/ui/Toast'

/** Monta as rotas informadas com os mesmos provedores do app, contra o servidor simulado (MSW). */
export function renderizarRotas(rotas: RouteObject[], inicial = '/') {
  const roteador = createMemoryRouter(rotas, { initialEntries: [inicial] })
  render(
    <QueryClientProvider client={criarClienteQuery()}>
      <ProvedorPreferencias>
        <ProvedorToast>
          <ProvedorAutenticacao>
            <RouterProvider router={roteador} />
          </ProvedorAutenticacao>
        </ProvedorToast>
      </ProvedorPreferencias>
    </QueryClientProvider>,
  )
  return { roteador }
}
