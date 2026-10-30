import { render, screen } from '@testing-library/react'
import type { LeituraAtual } from '@/dominio/entidades'
import { ParametrosAtuais } from './componentes/Tanque'
import { ProvedorPreferencias } from './preferencias'

const TS = '2026-10-29T12:00:00Z'

function leitura(grandeza: LeituraAtual['grandeza'], valor: number): LeituraAtual {
  return { grandeza, valor, unidade: '', ts: TS, estimado: grandeza === 'od', baixa_confianca: false }
}

function renderizar(leituras: LeituraAtual[]) {
  render(
    <ProvedorPreferencias>
      <ParametrosAtuais leituras={leituras} especie={null} ultimaLeitura={TS} agora={Date.parse(TS)} />
    </ProvedorPreferencias>,
  )
}

beforeEach(() => localStorage.clear())

describe('% de saturação e alerta térmico no cartão do tanque', () => {
  it('mostra o % de saturação do OD corrigido pela altitude padrão (760 m)', () => {
    renderizar([leitura('temperatura', 25), leitura('ph', 7.2), leitura('od', 6)])
    // 6 / 7,52 mg/L (saturação a 25 °C e 760 m) = 80%
    expect(screen.getByText('80% de saturação')).toBeInTheDocument()
    expect(screen.queryByText('Oxigênio baixo para água quente')).not.toBeInTheDocument()
  })

  it('usa a altitude salva nas preferências', () => {
    localStorage.setItem('painel-aquicola:preferencias', JSON.stringify({ altitudeM: 0 }))
    renderizar([leitura('temperatura', 25), leitura('od', 6)])
    // 6 / 8,26 mg/L ao nível do mar = 73%
    expect(screen.getByText('73% de saturação')).toBeInTheDocument()
  })

  it('avisa oxigênio baixo com água quente', () => {
    renderizar([leitura('temperatura', 29.5), leitura('od', 4.6)])
    expect(screen.getByText('Oxigênio baixo para água quente')).toBeInTheDocument()
  })

  it('sem temperatura não calcula a saturação', () => {
    renderizar([leitura('od', 6)])
    expect(screen.queryByText(/de saturação/)).not.toBeInTheDocument()
  })
})
