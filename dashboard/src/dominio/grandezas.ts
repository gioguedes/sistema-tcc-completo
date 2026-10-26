import { formatarNumero } from '@/compartilhado/formatacao'
import type { Grandeza } from './comum'
import type { Especie } from './entidades'

export interface FaixaIdeal {
  min: number
  /** `null` quando não há limite superior de risco (caso do OD). */
  max: number | null
}

interface InfoGrandeza {
  rotulo: string
  rotuloSimples: string
  unidade: string
  casas: number
  /** Cor da série nos gráficos (contraste ≥ 3:1 sobre branco). */
  cor: string
  estimado: boolean
  faixaIdeal: (especie: Especie) => FaixaIdeal | null
}

export const GRANDEZAS: Record<Grandeza, InfoGrandeza> = {
  temperatura: {
    rotulo: 'Temperatura',
    rotuloSimples: 'Temperatura da água',
    unidade: '°C',
    casas: 1,
    cor: 'var(--color-serie-temperatura)',
    estimado: false,
    faixaIdeal: (e) => ({ min: e.temp_min, max: e.temp_max }),
  },
  ph: {
    rotulo: 'pH',
    rotuloSimples: 'Acidez da água (pH)',
    unidade: '',
    casas: 1,
    cor: 'var(--color-serie-ph)',
    estimado: false,
    faixaIdeal: (e) => ({ min: e.ph_min, max: e.ph_max }),
  },
  turbidez: {
    rotulo: 'Turbidez',
    rotuloSimples: 'Água turva (turbidez)',
    unidade: 'NTU',
    casas: 0,
    cor: 'var(--color-serie-turbidez)',
    estimado: false,
    // A tabela `especies` não define faixa ideal de turbidez.
    faixaIdeal: () => null,
  },
  od: {
    rotulo: 'Oxigênio (estimado)',
    rotuloSimples: 'Oxigênio na água (estimado)',
    unidade: 'mg/L',
    casas: 1,
    cor: 'var(--color-serie-od)',
    estimado: true,
    // OD alto não é risco para o peixe, só a hipóxia (regra do serviço de ML, ml/src/faixas.py).
    faixaIdeal: (e) => ({ min: e.od_min, max: null }),
  },
}

/** Ordem de exibição usada no Figma. */
export const ORDEM_GRANDEZAS: Grandeza[] = ['temperatura', 'ph', 'turbidez', 'od']

export function rotuloGrandeza(g: Grandeza, linguagemSimples = false): string {
  return linguagemSimples ? GRANDEZAS[g].rotuloSimples : GRANDEZAS[g].rotulo
}

export function formatarValor(g: Grandeza, valor: number): string {
  const { unidade, casas } = GRANDEZAS[g]
  const numero = formatarNumero(valor, casas)
  return unidade ? `${numero} ${unidade}` : numero
}

export function formatarFaixa(g: Grandeza, faixa: FaixaIdeal): string {
  const { unidade, casas } = GRANDEZAS[g]
  const texto =
    faixa.max === null
      ? `a partir de ${formatarNumero(faixa.min, casas)}`
      : `${formatarNumero(faixa.min, casas)}–${formatarNumero(faixa.max, casas)}`
  return unidade ? `${texto} ${unidade}` : texto
}

export function faixaIdealDe(g: Grandeza, especie: Especie | null | undefined): FaixaIdeal | null {
  return especie ? GRANDEZAS[g].faixaIdeal(especie) : null
}
