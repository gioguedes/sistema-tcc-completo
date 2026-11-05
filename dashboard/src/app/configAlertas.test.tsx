import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { entrar } from '@/infra/api/autenticacao'
import { sessao } from '@/infra/api/sessao'
import { renderizarRotas } from '@/testes/renderizar'
import { servidor } from '@/testes/servidor'
import PaginaConfiguracoes from './funcionalidades/ajustes/PaginaConfiguracoes'
import { RotaProtegida } from './funcionalidades/autenticacao/Guardas'

const rotas = [{ path: '/configuracoes', element: <RotaProtegida><PaginaConfiguracoes /></RotaProtegida> }]
const espera = { timeout: 4000 }
const URL_WEBHOOK = 'https://n8n.exemplo.test/webhook/abc'

afterEach(() => sessao.definirToken(null))

async function abrirComo(email: string) {
  await entrar({ email, senha: 'aquicola-demo', lembrar: false })
  renderizarRotas(rotas, '/configuracoes')
  await screen.findByRole('heading', { name: 'Minha conta' }, espera)
}

const abrirComoAdmin = async () => {
  await abrirComo('admin@painelaquicola.test')
  return screen.findByRole('textbox', { name: /URL do webhook/ }, espera)
}

describe('webhook dos alertas nas configurações', { timeout: 20_000 }, () => {
  it('o administrador salva a URL e depois desliga os alertas', async () => {
    const usuario = userEvent.setup()
    const campo = await abrirComoAdmin()
    expect(screen.getByText('Alertas desligados: nenhum webhook configurado.')).toBeInTheDocument()

    await usuario.type(campo, URL_WEBHOOK)
    await usuario.click(screen.getByRole('button', { name: 'Salvar webhook' }))
    expect(await screen.findByText('Webhook dos alertas salvo.', {}, espera)).toBeInTheDocument()
    expect(await screen.findByText('Alertas ligados: o sistema avisa este webhook.', {}, espera)).toBeInTheDocument()

    await usuario.clear(campo)
    await usuario.click(screen.getByRole('button', { name: 'Salvar webhook' }))
    expect(await screen.findByText('Alertas desligados: nenhum webhook configurado.', {}, espera)).toBeInTheDocument()
  })

  it('recusa um endereço inválido sem chamar a API', async () => {
    let chamou = false
    servidor.use(
      http.put('*/api/v1/configuracoes/alertas', () => {
        chamou = true
        return HttpResponse.json({ webhook_url: null, atualizado_em: null })
      }),
    )
    const usuario = userEvent.setup()
    const campo = await abrirComoAdmin()

    await usuario.type(campo, 'n8n.exemplo.test/webhook')
    await usuario.click(screen.getByRole('button', { name: 'Salvar webhook' }))

    expect(await screen.findByText('Informe uma URL completa, começando com http:// ou https://.', {}, espera)).toBeInTheDocument()
    expect(chamou).toBe(false)
  })

  it('mostra no campo o erro devolvido pela API', async () => {
    servidor.use(
      http.put('*/api/v1/configuracoes/alertas', () =>
        HttpResponse.json(
          { detail: [{ loc: ['body', 'webhook_url'], msg: 'Use no máximo 500 caracteres.', type: 'url_longa' }] },
          { status: 422 },
        ),
      ),
    )
    const usuario = userEvent.setup()
    const campo = await abrirComoAdmin()

    await usuario.type(campo, URL_WEBHOOK)
    await usuario.click(screen.getByRole('button', { name: 'Salvar webhook' }))

    expect(await screen.findByText('Use no máximo 500 caracteres.', {}, espera)).toBeInTheDocument()
  })

  it('quem não é administrador não vê a URL e nem consulta a API', async () => {
    let consultou = false
    servidor.use(
      http.get('*/api/v1/configuracoes/alertas', () => {
        consultou = true
        return HttpResponse.json({ webhook_url: URL_WEBHOOK, atualizado_em: null })
      }),
    )
    await abrirComo('produtor@painelaquicola.test')

    expect(screen.queryByRole('textbox', { name: /URL do webhook/ })).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Preferências' })).toBeInTheDocument())
    expect(consultou).toBe(false)
  })
})
