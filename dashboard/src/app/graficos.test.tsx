import { render, screen, within } from '@testing-library/react'
import { respostaLeituras } from '@/dominio/entidades'
import { GraficosPorGrandeza } from './componentes/Graficos'
import { ProvedorPreferencias } from './preferencias'

const resposta = respostaLeituras.parse({
  id_tanque: 1,
  bucket: '5m',
  desde: '2026-11-05T00:00:00Z',
  ate: '2026-11-05T01:00:00Z',
  series: [
    { grandeza: 'temperatura', unidade: '°C', pontos: [{ ts: '2026-11-05T00:30:00Z', valor: 25.2 }] },
    { grandeza: 'od', unidade: 'mg/L', estimado: true, pontos: [{ ts: '2026-11-05T00:30:00Z', valor: 7.1 }] },
  ],
})

beforeEach(() => localStorage.clear())

describe('legenda dos gráficos por grandeza', () => {
  it('chama a série do OD de estimativa e a dos sensores de leitura', () => {
    render(
      <ProvedorPreferencias>
        <GraficosPorGrandeza resposta={resposta} especie={null} />
      </ProvedorPreferencias>,
    )

    const od = screen.getByRole('region', { name: 'Oxigênio (estimado)' })
    expect(within(od).getByText('Estimativa do modelo')).toBeInTheDocument()
    expect(within(od).queryByText('Leituras do sensor')).not.toBeInTheDocument()

    const temperatura = screen.getByRole('region', { name: 'Temperatura' })
    expect(within(temperatura).getByText('Leituras do sensor')).toBeInTheDocument()
  })
})
