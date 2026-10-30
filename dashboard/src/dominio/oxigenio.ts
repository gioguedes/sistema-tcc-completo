/**
 * OD de saturação em água doce, Benson e Krause (1984), na forma do APHA 4500-O e do memorando
 * USGS OWQ 2011.03, com a correção de pressão pela altitude. Para o peixe, o que importa é o %
 * de saturação, não a concentração (Chabot e Guénette, 2013).
 */

/** Pressão barométrica (atm) da atmosfera padrão na altitude dada. */
export function pressaoAtm(altitudeM: number): number {
  return (1 - 2.25577e-5 * altitudeM) ** 5.25588
}

export function odSaturacao(temperaturaC: number, altitudeM = 0): number {
  const t = temperaturaC + 273.15
  const ln1atm = -139.34411 + 1.575701e5 / t - 6.642308e7 / t ** 2 + 1.2438e10 / t ** 3 - 8.621949e11 / t ** 4
  const p = pressaoAtm(altitudeM)
  const vapor = Math.exp(11.8571 - 3840.7 / t - 216961 / t ** 2)
  const theta = 0.000975 - 1.426e-5 * temperaturaC + 6.436e-8 * temperaturaC ** 2
  return Math.exp(ln1atm) * p * (((1 - vapor / p) * (1 - theta * p)) / ((1 - vapor) * (1 - theta)))
}

export function percentualSaturacao(odMgL: number, temperaturaC: number, altitudeM = 0): number {
  return (100 * odMgL) / odSaturacao(temperaturaC, altitudeM)
}

/**
 * Água quente pede mais oxigênio do peixe e dissolve menos (Chabot e Guénette, 2013); abaixo de
 * 5 mg/L o peixe já sofre estresse (Bello et al., 2017). O aviso não muda o nível de risco do ML.
 */
export const OD_ALERTA_TERMICO = 5
export const TEMPERATURA_ALERTA_TERMICO = 28

export function alertaTermico(odMgL: number, temperaturaC: number): boolean {
  return odMgL < OD_ALERTA_TERMICO && temperaturaC > TEMPERATURA_ALERTA_TERMICO
}
