/**
 * Cópia, para o servidor SIMULADO, da regra de `ml/src/faixas.py` (spec do ML, correção de 30/09/2026).
 * A interface não usa este arquivo: o nível sempre chega pronto da API.
 */
import type { Grandeza, NivelRisco } from '@/dominio/comum'

const MARGEM_RELATIVA = 0.1
const OD_CRITICO_ABSOLUTO = 3.0
const ORDEM: NivelRisco[] = ['otimo', 'atencao', 'critico']

export interface FaixaSimulada {
  ph_min: string
  ph_max: string
  temp_min: string
  temp_max: string
  od_min: string
  od_max: string
}

function limites(g: Grandeza, f: FaixaSimulada): [number, number] {
  if (g === 'ph') return [Number(f.ph_min), Number(f.ph_max)]
  if (g === 'temperatura') return [Number(f.temp_min), Number(f.temp_max)]
  return [Number(f.od_min), Number(f.od_max)]
}

export function nivelPorFaixa(valor: number, g: Grandeza, faixa: FaixaSimulada): NivelRisco {
  const [minimo, maximo] = limites(g, faixa)
  const margem = MARGEM_RELATIVA * (maximo - minimo)
  if (g === 'od') {
    // OD alto não é risco: só a hipóxia conta
    if (valor < minimo || valor < OD_CRITICO_ABSOLUTO) return 'critico'
    return valor >= minimo + margem ? 'otimo' : 'atencao'
  }
  if (valor < minimo || valor > maximo) return 'critico'
  return valor >= minimo + margem && valor <= maximo - margem ? 'otimo' : 'atencao'
}

/** Pior nível entre pH, temperatura e OD (`nivel_geral` do ML). */
export function nivelGeral(ph: number, temperatura: number, od: number, faixa: FaixaSimulada): NivelRisco {
  const niveis = [nivelPorFaixa(ph, 'ph', faixa), nivelPorFaixa(temperatura, 'temperatura', faixa), nivelPorFaixa(od, 'od', faixa)]
  return ORDEM[Math.max(...niveis.map((n) => ORDEM.indexOf(n)))]!
}
