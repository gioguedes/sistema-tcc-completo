import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { entrar } from '@/infra/api/autenticacao'
import { sessao } from '@/infra/api/sessao'
import { renderizarRotas } from '@/testes/renderizar'
import { servidor } from '@/testes/servidor'
import { RotaProtegida } from './funcionalidades/autenticacao/Guardas'
import PaginaDetalheTanque from './funcionalidades/tanques/PaginaDetalheTanque'

const rotas = [{ path: '/tanques/:id', element: <RotaProtegida><PaginaDetalheTanque /></RotaProtegida> }]

// Folga maior que o 1 s padrão em cada espera: o controle depende da sessão, do tanque e dos dispositivos,
// e o comando, da mutação e de uma nova consulta. Com a máquina carregada (logo após o npm ci, ou com
// outras suítes rodando ao lado) isso passava do limite.
const espera = { timeout: 4000 }

afterEach(() => sessao.definirToken(null))

/** Produtor no detalhe do Tanque Norte, cujo nó está online no servidor simulado. */
async function abrirControleDoAerador() {
  await entrar({ email: 'produtor@painelaquicola.test', senha: 'aquicola-demo', lembrar: false })
  renderizarRotas(rotas, '/tanques/1')
  return screen.findByRole('group', { name: 'Aerador' }, espera)
}

// a soma das esperas passa dos 5 s padrão por teste
describe('aerador (F-02)', { timeout: 20_000 }, () => {
  it('o produtor desliga o aerador com confirmação e passa a ver o último comando', async () => {
    const usuario = userEvent.setup()
    const controle = await abrirControleDoAerador()
    expect(within(controle).getByText('Nenhum comando enviado ainda.')).toBeInTheDocument()

    await usuario.click(within(controle).getByRole('button', { name: 'Desligar' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Desligar o aerador?' }, espera)
    await usuario.click(within(dialogo).getByRole('button', { name: 'Desligar aerador' }))

    expect(
      await screen.findByText('Comando enviado. O aerador do Tanque Norte deve desligar em instantes.', {}, espera),
    ).toBeInTheDocument()
    expect(await within(controle).findByText('Último comando: desligar, agora.', {}, espera)).toBeInTheDocument()
  })

  it('avisa quando a API não consegue entregar o comando ao broker (503)', async () => {
    servidor.use(
      http.post('*/api/v1/dispositivos/:id/aerador', () =>
        HttpResponse.json({ detail: 'Não foi possível enviar o comando ao nó sensor.' }, { status: 503 }),
      ),
    )
    const usuario = userEvent.setup()
    const controle = await abrirControleDoAerador()

    await usuario.click(within(controle).getByRole('button', { name: 'Ligar' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Ligar o aerador?' }, espera)
    await usuario.click(within(dialogo).getByRole('button', { name: 'Ligar aerador' }))

    expect(
      await screen.findByText('Não foi possível enviar o comando ao nó sensor. Tente novamente.', {}, espera),
    ).toBeInTheDocument()
    expect(within(controle).getByText('Nenhum comando enviado ainda.')).toBeInTheDocument()
  })
})
