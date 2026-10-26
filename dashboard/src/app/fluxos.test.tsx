import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useParams } from 'react-router'
import { entrar } from '@/infra/api/autenticacao'
import { sessao } from '@/infra/api/sessao'
import { renderizarRotas } from '@/testes/renderizar'
import PaginaNovoTanque from './funcionalidades/admin/PaginaNovoTanque'
import PaginaLogin from './funcionalidades/autenticacao/PaginaLogin'
import { RotaProtegida, SomenteAdmin } from './funcionalidades/autenticacao/Guardas'

const SENHA = 'aquicola-demo'

function DetalheFalso() {
  const { id } = useParams()
  return <p>Detalhe do tanque {id}</p>
}

const rotas = [
  { path: '/entrar', element: <PaginaLogin /> },
  { path: '/', element: <RotaProtegida><p>Área protegida</p></RotaProtegida> },
  {
    path: '/tanques/novo',
    element: (
      <RotaProtegida>
        <SomenteAdmin>
          <PaginaNovoTanque />
        </SomenteAdmin>
      </RotaProtegida>
    ),
  },
  { path: '/tanques/:id', element: <RotaProtegida><DetalheFalso /></RotaProtegida> },
]

afterEach(() => sessao.definirToken(null))

describe('autenticação', () => {
  it('redireciona para o login, valida campos, recusa senha errada e entra com a correta', async () => {
    const usuario = userEvent.setup()
    const { roteador } = renderizarRotas(rotas, '/')

    const entrarBotao = await screen.findByRole('button', { name: 'Entrar' })
    expect(roteador.state.location.pathname).toBe('/entrar')

    await usuario.click(entrarBotao)
    expect(await screen.findByText('Informe seu e-mail.')).toBeInTheDocument()
    expect(screen.getByText('Informe sua senha.')).toBeInTheDocument()

    await usuario.type(screen.getByLabelText('E-mail'), 'produtor@painelaquicola.test')
    await usuario.type(screen.getByLabelText('Senha'), 'senha-errada')
    await usuario.click(entrarBotao)
    expect(await screen.findByText('E-mail ou senha incorretos.')).toBeInTheDocument()

    await usuario.clear(screen.getByLabelText('Senha'))
    await usuario.type(screen.getByLabelText('Senha'), SENHA)
    await usuario.click(entrarBotao)
    expect(await screen.findByText('Área protegida')).toBeInTheDocument()
    expect(roteador.state.location.pathname).toBe('/')
  })

  it('restaura a sessão existente ao abrir o app (sem pedir login de novo)', async () => {
    await entrar({ email: 'produtor@painelaquicola.test', senha: SENHA, lembrar: false })
    sessao.definirToken(null) // simula recarregar a página: o token em memória se perde, o cookie de renovação não
    renderizarRotas(rotas, '/')
    expect(await screen.findByText('Área protegida')).toBeInTheDocument()
  })
})

describe('UC01 — cadastrar tanque e dispositivo', () => {
  it('bloqueia o cadastro para o perfil Produtor', async () => {
    await entrar({ email: 'produtor@painelaquicola.test', senha: SENHA, lembrar: false })
    renderizarRotas(rotas, '/tanques/novo')
    expect(await screen.findByText('Acesso restrito')).toBeInTheDocument()
  })

  it('mostra o MAC duplicado no campo (409) e cadastra após a correção', async () => {
    await entrar({ email: 'admin@painelaquicola.test', senha: SENHA, lembrar: false })
    const usuario = userEvent.setup()
    const { roteador } = renderizarRotas(rotas, '/tanques/novo')

    await usuario.type(await screen.findByLabelText(/^Nome do tanque/), 'Tanque Experimental')
    await waitFor(() => expect(screen.getByRole('option', { name: /Tilápia do Nilo/ })).toBeInTheDocument())
    await usuario.selectOptions(screen.getByLabelText(/^Espécie/), '1')
    await usuario.type(screen.getByLabelText(/^Volume/), '80')
    await usuario.type(screen.getByLabelText(/^Nome do dispositivo/), 'Nó sensor Experimental')
    await usuario.type(screen.getByLabelText(/^Endereço MAC/), 'A4F00F643C70')
    await usuario.click(screen.getByRole('button', { name: 'Cadastrar tanque' }))

    expect(await screen.findByText('Este endereço MAC já está cadastrado em outro dispositivo.')).toBeInTheDocument()
    expect(screen.getByLabelText(/^Endereço MAC/)).toHaveAttribute('aria-invalid', 'true')

    await usuario.clear(screen.getByLabelText(/^Endereço MAC/))
    await usuario.type(screen.getByLabelText(/^Endereço MAC/), 'a4:f0:0f:64:3c:99')
    await usuario.click(screen.getByRole('button', { name: 'Cadastrar tanque' }))

    expect(await screen.findByText('Detalhe do tanque 6')).toBeInTheDocument()
    expect(roteador.state.location.pathname).toBe('/tanques/6')
  })
})
