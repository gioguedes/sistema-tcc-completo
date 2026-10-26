import type { ComponentType } from 'react'
import { createBrowserRouter } from 'react-router'
import { RotaProtegida, SomenteAdmin, TelaCarregamento } from './funcionalidades/autenticacao/Guardas'
import { LayoutApp } from './layouts/LayoutApp'
import { PaginaErro, PaginaNaoEncontrada } from './PaginasSistema'

/** Cada tela vira um arquivo separado no build e só é baixada quando acessada. */
const pagina = (importar: () => Promise<{ default: ComponentType }>) => async () => ({
  Component: (await importar()).default,
})

const paginaAdmin = (importar: () => Promise<{ default: ComponentType }>) => async () => {
  const { default: Pagina } = await importar()
  return {
    Component: () => (
      <SomenteAdmin>
        <Pagina />
      </SomenteAdmin>
    ),
  }
}

export const roteador = createBrowserRouter([
  {
    path: '/entrar',
    lazy: pagina(() => import('./funcionalidades/autenticacao/PaginaLogin')),
    hydrateFallbackElement: <TelaCarregamento />,
    errorElement: <PaginaErro />,
  },
  {
    element: (
      <RotaProtegida>
        <LayoutApp />
      </RotaProtegida>
    ),
    hydrateFallbackElement: <TelaCarregamento />,
    errorElement: <PaginaErro />,
    children: [
      { index: true, handle: { titulo: 'Meus tanques' }, lazy: pagina(() => import('./funcionalidades/tanques/PaginaInicio')) },
      { path: 'tanques', handle: { titulo: 'Tanques' }, lazy: pagina(() => import('./funcionalidades/tanques/PaginaTanques')) },
      { path: 'tanques/novo', handle: { titulo: 'Novo tanque' }, lazy: paginaAdmin(() => import('./funcionalidades/admin/PaginaNovoTanque')) },
      { path: 'tanques/:id', handle: { titulo: 'Tanque' }, lazy: pagina(() => import('./funcionalidades/tanques/PaginaDetalheTanque')) },
      { path: 'tanques/:id/editar', handle: { titulo: 'Editar tanque' }, lazy: paginaAdmin(() => import('./funcionalidades/admin/PaginaEditarTanque')) },
      { path: 'historico', handle: { titulo: 'Histórico' }, lazy: pagina(() => import('./funcionalidades/historico/PaginaHistorico')) },
      { path: 'relatorios', handle: { titulo: 'Relatórios' }, lazy: pagina(() => import('./funcionalidades/historico/PaginaRelatorios')) },
      { path: 'previsao', handle: { titulo: 'Previsão' }, lazy: pagina(() => import('./funcionalidades/previsao/PaginaPrevisao')) },
      { path: 'alertas', handle: { titulo: 'Alertas' }, lazy: pagina(() => import('./funcionalidades/alertas/PaginaAlertas')) },
      { path: 'eventos', handle: { titulo: 'Eventos' }, lazy: pagina(() => import('./funcionalidades/eventos/PaginaEventos')) },
      { path: 'configuracoes', handle: { titulo: 'Ajustes' }, lazy: pagina(() => import('./funcionalidades/ajustes/PaginaConfiguracoes')) },
      { path: '*', handle: { titulo: 'Página não encontrada' }, element: <PaginaNaoEncontrada /> },
    ],
  },
])
