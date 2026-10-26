import { http, HttpResponse } from 'msw'
import { z } from 'zod'
import { servidor } from '@/testes/servidor'
import { numero } from '@/dominio/comum'
import { requisitar } from './cliente'
import { ErroApi } from './erros'
import { sessao } from './sessao'

const API = '*/api/v1'

async function capturar(promessa: Promise<unknown>): Promise<ErroApi> {
  try {
    await promessa
  } catch (erro) {
    if (erro instanceof ErroApi) return erro
    throw erro
  }
  throw new Error('a requisição deveria ter falhado')
}

describe('cliente HTTP', () => {
  afterEach(() => sessao.definirToken(null))

  it('converte erro 500 em mensagem amigável, sem expor o status técnico', async () => {
    servidor.use(http.get(`${API}/teste`, () => HttpResponse.json({ detail: 'Internal Server Error' }, { status: 500 })))
    const erro = await capturar(requisitar('/teste', z.object({})))
    expect(erro.tipo).toBe('servidor')
    expect(erro.message).toBe('Ocorreu um erro no servidor. Tente novamente em instantes.')
  })

  it('avisa quando a função ainda não existe na API (501)', async () => {
    servidor.use(
      http.post(`${API}/teste`, () =>
        HttpResponse.json({ detail: 'Esta função ainda não está disponível nesta versão da API.' }, { status: 501 }),
      ),
    )
    const erro = await capturar(requisitar('/teste', z.object({}), { metodo: 'POST', corpo: {} }))
    expect(erro.tipo).toBe('indisponivel')
    expect(erro.message).toBe('Esta função ainda não está disponível no servidor.')
  })

  it('identifica API indisponível como erro de rede', async () => {
    servidor.use(http.get(`${API}/teste`, () => HttpResponse.error()))
    const erro = await capturar(requisitar('/teste', z.object({})))
    expect(erro.tipo).toBe('rede')
  })

  it('leva os erros 422 do FastAPI para os campos, traduzindo mensagens do Pydantic', async () => {
    servidor.use(
      http.post(`${API}/teste`, () =>
        HttpResponse.json(
          {
            detail: [
              { loc: ['body', 'nome'], msg: 'Field required', type: 'missing' },
              { loc: ['body', 'dispositivo', 'mac_address'], msg: 'MAC inválido.', type: 'value_error' },
            ],
          },
          { status: 422 },
        ),
      ),
    )
    const erro = await capturar(requisitar('/teste', null, { metodo: 'POST', corpo: {} }))
    expect(erro.tipo).toBe('validacao')
    expect(erro.campos).toEqual({ nome: 'Campo obrigatório.', 'dispositivo.mac_address': 'MAC inválido.' })
  })

  it('renova a sessão uma única vez ao receber 401 e repete a requisição', async () => {
    let renovacoes = 0
    servidor.use(
      http.post(`${API}/auth/refresh`, () => {
        renovacoes++
        return HttpResponse.json({ access_token: 'novo', expira_em: new Date().toISOString() })
      }),
      http.get(`${API}/protegido`, ({ request }) =>
        request.headers.get('Authorization') === 'Bearer novo'
          ? HttpResponse.json({ ok: true })
          : HttpResponse.json({ detail: 'Não autenticado.' }, { status: 401 }),
      ),
    )
    sessao.definirToken('vencido')
    const [a, b] = await Promise.all([
      requisitar('/protegido', z.object({ ok: z.boolean() })),
      requisitar('/protegido', z.object({ ok: z.boolean() })),
    ])
    expect(a.ok && b.ok).toBe(true)
    expect(renovacoes).toBe(1)
  })

  it('encerra a sessão e avisa a interface quando a renovação falha', async () => {
    const aoExpirar = vi.fn()
    const cancelar = sessao.aoExpirar(aoExpirar)
    servidor.use(
      http.post(`${API}/auth/refresh`, () => HttpResponse.json({ detail: 'Sessão expirada.' }, { status: 401 })),
      http.get(`${API}/protegido`, () => HttpResponse.json({ detail: 'Não autenticado.' }, { status: 401 })),
    )
    sessao.definirToken('vencido')
    const erro = await capturar(requisitar('/protegido', z.object({})))
    cancelar()
    expect(erro.tipo).toBe('sessao_expirada')
    expect(erro.message).toBe('Sua sessão expirou. Entre novamente.')
    expect(aoExpirar).toHaveBeenCalledOnce()
    expect(sessao.token()).toBeNull()
  })

  it('rejeita resposta fora do contrato com mensagem amigável', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    servidor.use(http.get(`${API}/teste`, () => HttpResponse.json({ id: 'não é número' })))
    const erro = await capturar(requisitar('/teste', z.object({ id: z.number() })))
    expect(erro.tipo).toBe('resposta_invalida')
    expect(erro.message).toBe('Recebemos uma resposta inesperada do servidor.')
  })

  it('aceita NUMERIC serializado como string (padrão do Pydantic para Decimal)', async () => {
    servidor.use(http.get(`${API}/teste`, () => HttpResponse.json({ volume: '500.00', ph: 7.2 })))
    const dados = await requisitar('/teste', z.object({ volume: numero, ph: numero }))
    expect(dados).toEqual({ volume: 500, ph: 7.2 })
  })
})
