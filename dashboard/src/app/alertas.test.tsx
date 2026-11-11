import { render, screen } from '@testing-library/react'
import { alertasPaginados, eventosPaginados } from '@/dominio/entidades'
import { ItemAlerta, ItemEventoFeed } from './componentes/Alertas'

const AGORA = Date.parse('2026-11-10T23:00:00Z')
const TANQUE = { id_tanque: 1, tanque_nome: 'Tanque bancada TCC' }
const NORMAL = 'Tanque bancada TCC: água fora da condição crítica (pH 8,10 e temperatura 26,0 °C).'
const PH_ALTO = 'Tanque bancada TCC: risco crítico. pH 9,18, acima do limite de 8,5.'

// corpos no formato que a API devolve (backend/tests/api/test_alertas.py), com os microssegundos do banco
const { itens: alertas } = alertasPaginados.parse({
  itens: [
    {
      ...TANQUE, id: 3, id_previsao: 41, mensagem: NORMAL, nivel_risco: 'otimo', parametro: null,
      recomendacoes: ['Nenhuma ação necessária. Mantenha o acompanhamento.'],
      canal: 'whatsapp', status: 'enviado', ts_envio: '2026-11-10T22:50:05.123456Z', criado_em: '2026-11-10T22:50:05.123456Z',
    },
    {
      ...TANQUE, id: 2, id_previsao: null, mensagem: PH_ALTO, nivel_risco: 'critico', parametro: 'ph',
      recomendacoes: ['Confira o sensor e a água.'],
      canal: 'whatsapp', status: 'falha', ts_envio: null, criado_em: '2026-11-10T22:40:05.5Z',
    },
    {
      ...TANQUE, id: 1, id_previsao: null, mensagem: 'Alerta gravado antes das colunas novas.', nivel_risco: null,
      parametro: null, recomendacoes: [], canal: 'whatsapp', status: 'pendente', ts_envio: null,
      criado_em: '2026-11-10T22:30:00Z',
    },
  ],
  total: 3,
  pagina: 1,
  por_pagina: 10,
})
const [normal, critico, semNivel] = alertas

const mostrar = (alerta: (typeof alertas)[number]) =>
  render(
    <ul>
      <ItemAlerta alerta={alerta} agora={AGORA} />
    </ul>,
  )

describe('alertas gravados pelo serviço de alertas', () => {
  it('o aviso de fim da condição crítica não aparece como alerta de atenção', () => {
    mostrar(normal)
    expect(screen.getByText('Condição normal — Tanque bancada TCC')).toBeInTheDocument()
    expect(screen.getByText(NORMAL)).toBeInTheDocument()
  })

  it('o alerta enviado mostra o canal, sem tempo de envio', () => {
    mostrar(normal)
    expect(screen.getByText('Enviado via WhatsApp')).toBeInTheDocument()
    expect(screen.queryByText(/ em \d+ s/)).not.toBeInTheDocument()
  })

  it('o alerta crítico que não saiu mostra a falha no envio', () => {
    mostrar(critico)
    expect(screen.getByText('Alerta crítico — Tanque bancada TCC')).toBeInTheDocument()
    expect(screen.getByText('Falha no envio')).toBeInTheDocument()
  })

  it('alerta sem nível gravado aparece com título neutro', () => {
    mostrar(semNivel)
    expect(screen.getByText('Alerta — Tanque bancada TCC')).toBeInTheDocument()
    expect(screen.getByText('Envio pendente')).toBeInTheDocument()
  })

  it('no feed de eventos o aviso de normal também não vira atenção', () => {
    const { itens } = eventosPaginados.parse({
      itens: [
        { ...TANQUE, tipo: 'alerta', id: 'alerta-3', ocorrido_em: '2026-11-10T22:50:05.123456Z', nivel_risco: 'otimo', mensagem: NORMAL },
        { ...TANQUE, tipo: 'alerta', id: 'alerta-2', ocorrido_em: '2026-11-10T22:40:05.5Z', nivel_risco: 'critico', mensagem: PH_ALTO },
      ],
      total: 2,
      pagina: 1,
      por_pagina: 10,
    })
    render(
      <ul>
        {itens.map((e) => (
          <ItemEventoFeed key={e.id} evento={e} agora={AGORA} />
        ))}
      </ul>,
    )
    expect(screen.getByText('Condição normal — Tanque bancada TCC')).toBeInTheDocument()
    expect(screen.getByText('Alerta crítico — Tanque bancada TCC')).toBeInTheDocument()
  })
})
