import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { entrar } from '@/infra/api/autenticacao'
import { sessao } from '@/infra/api/sessao'
import { lerUltimaLeitura, salvarUltimaLeitura } from '@/infra/armazenamento/ultimaLeitura'
import { renderizarRotas } from '@/testes/renderizar'
import { servidor } from '@/testes/servidor'
import { RotaProtegida } from './funcionalidades/autenticacao/Guardas'
import PaginaLogin from './funcionalidades/autenticacao/PaginaLogin'
import PaginaInicio from './funcionalidades/tanques/PaginaInicio'

// jsdom não tem IndexedDB: o armazenamento vira um Map em memória
const armazenado = vi.hoisted(() => new Map<string, unknown>())
vi.mock('idb-keyval', () => ({
  get: async (chave: string) => armazenado.get(chave),
  set: async (chave: string, valor: unknown) => void armazenado.set(chave, valor),
  del: async (chave: string) => void armazenado.delete(chave),
}))

const rotas = [
  { path: '/entrar', element: <PaginaLogin /> },
  { path: '/', element: <RotaProtegida><PaginaInicio /></RotaProtegida> },
]

const semRede = () => servidor.use(http.post('*/api/v1/auth/refresh', () => HttpResponse.error()))

afterEach(() => {
  sessao.definirToken(null)
  armazenado.clear()
})

describe('abertura sem conexão (PWA, TC2 §9)', () => {
  it('guarda a lista de tanques recebida como a última leitura do aparelho', async () => {
    await entrar({ email: 'produtor@painelaquicola.test', senha: 'aquicola-demo', lembrar: false })
    renderizarRotas(rotas, '/')
    expect(await screen.findByRole('heading', { name: /Boa (noite|tarde)|Bom dia/ })).toBeInTheDocument()
    await waitFor(async () => expect((await lerUltimaLeitura())?.tanques.length).toBeGreaterThan(0))
  })

  it('mostra a última leitura salva, com o horário e o aviso de desatualizada', async () => {
    const medidoEm = new Date(Date.now() - 3 * 3_600_000).toISOString()
    await salvarUltimaLeitura([
      {
        id: 1,
        nome: 'Tanque Norte',
        volume_litros: 80,
        quantidade_peixes: 12,
        data_povoamento: null,
        status: 'ativo',
        criado_em: '2026-09-01T12:00:00Z',
        especie: null,
        nivel_risco: 'otimo',
        ultima_leitura_em: medidoEm,
        ultimas_leituras: [{ grandeza: 'ph', valor: 7.1, unidade: 'pH', ts: medidoEm, estimado: false, baixa_confianca: false }],
        dispositivos: [],
      },
    ])
    semRede()
    renderizarRotas(rotas, '/')

    expect(await screen.findByRole('heading', { name: 'Última leitura salva' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tanque Norte' })).toBeInTheDocument()
    expect(screen.getByText(/podem não mostrar a situação atual dos tanques/)).toBeInTheDocument()
    expect(screen.getByText(/^Medido há 3 h/)).toBeInTheDocument()
  })

  it('sem leitura salva, explica e oferece nova tentativa, que entra quando o servidor volta', async () => {
    await entrar({ email: 'produtor@painelaquicola.test', senha: 'aquicola-demo', lembrar: false })
    sessao.definirToken(null)
    semRede()
    const usuario = userEvent.setup()
    renderizarRotas(rotas, '/')

    expect(await screen.findByText(/Ainda não há leitura salva neste aparelho/)).toBeInTheDocument()
    servidor.resetHandlers()
    await usuario.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(await screen.findByRole('heading', { name: /Boa (noite|tarde)|Bom dia/ })).toBeInTheDocument()
  })

  it('apaga a cópia local quando a sessão acabou de vez (401) e leva ao login', async () => {
    await salvarUltimaLeitura([])
    const { roteador } = renderizarRotas(rotas, '/')
    expect(await screen.findByRole('button', { name: 'Entrar' })).toBeInTheDocument()
    expect(roteador.state.location.pathname).toBe('/entrar')
    await waitFor(async () => expect(await lerUltimaLeitura()).toBeNull())
  })
})
