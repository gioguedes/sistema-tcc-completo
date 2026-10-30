import { alertaTermico, odSaturacao, percentualSaturacao, pressaoAtm } from './oxigenio'

// Valores de referência: tabela de solubilidade do USGS (OWQ 2011.03) ao nível do mar.
describe('OD de saturação', () => {
  it('bate com a tabela ao nível do mar', () => {
    expect(odSaturacao(20)).toBeCloseTo(9.09, 2)
    expect(odSaturacao(25)).toBeCloseTo(8.26, 2)
    expect(odSaturacao(30)).toBeCloseTo(7.56, 2)
  })

  it('cai com a altitude: cerca de 9% a menos em São Paulo (760 m)', () => {
    expect(pressaoAtm(760)).toBeCloseTo(0.913, 3)
    expect(odSaturacao(25, 760) / odSaturacao(25)).toBeCloseTo(0.91, 2)
  })

  it('o % de saturação usa a temperatura e a altitude', () => {
    expect(percentualSaturacao(odSaturacao(28), 28)).toBeCloseTo(100, 6)
    expect(percentualSaturacao(4, 28)).toBeCloseTo(51.1, 1)
    expect(percentualSaturacao(4, 28, 760)).toBeGreaterThan(percentualSaturacao(4, 28))
  })
})

describe('alerta de oxigênio baixo com água quente', () => {
  it('só avisa com OD abaixo de 5 mg/L e água acima de 28 °C', () => {
    expect(alertaTermico(4.8, 29)).toBe(true)
    expect(alertaTermico(4.8, 28)).toBe(false)
    expect(alertaTermico(5, 29)).toBe(false)
    expect(alertaTermico(6, 31)).toBe(false)
  })
})
