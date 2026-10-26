import type { Grandeza } from '@/dominio/comum'

export const MINUTO = 60_000
export const HORA = 60 * MINUTO
export const DIA = 24 * HORA

interface ParametroCenario {
  base: number
  /** Variação ao longo do dia, com pico no horário `pico`. */
  amplitude: number
  pico: number
  ruido: number
  /** Variação lenta (ciclo de 5 dias), para o histórico de 30 dias não ser repetitivo. */
  deriva: number
  min: number
  max: number
  casas: number
}

export interface CenarioSerie {
  semente: number
  parametros: Record<Grandeza, ParametroCenario>
  /** Tendência das últimas horas (ex.: "pH subindo"). */
  rampa?: { grandeza: Grandeza; variacao: number; horas: number }
}

/** Pseudoaleatório determinístico em [-1, 1]: o mesmo minuto sempre gera o mesmo valor. */
function ruido(semente: number, indice: number): number {
  let x = Math.imul(semente ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(indice, 0xc2b2ae35)
  x ^= x >>> 16
  x = Math.imul(x, 0x7feb352d)
  x ^= x >>> 15
  return ((x >>> 0) / 0xffffffff) * 2 - 1
}

const INDICE_GRANDEZA: Record<Grandeza, number> = { ph: 1, temperatura: 2, turbidez: 3, od: 4 }

function horaLocal(t: number): number {
  const d = new Date(t)
  return d.getHours() + d.getMinutes() / 60
}

export function valorEm(cenario: CenarioSerie, g: Grandeza, t: number, agora = Date.now()): number {
  const p = cenario.parametros[g]
  const diurno = Math.cos(((horaLocal(t) - p.pico) / 24) * 2 * Math.PI)
  const lento = Math.sin((t / (5 * DIA)) * 2 * Math.PI + cenario.semente)
  const minuto = Math.floor(t / MINUTO)
  let valor =
    p.base + p.amplitude * diurno + p.deriva * lento + p.ruido * ruido(cenario.semente * 7 + INDICE_GRANDEZA[g], minuto)

  const rampa = cenario.rampa
  if (rampa?.grandeza === g) {
    // Ancorada em blocos de 10 min para o gráfico não "tremer" a cada atualização.
    const referencia = Math.floor(agora / (10 * MINUTO)) * 10 * MINUTO
    const progresso = 1 - (referencia - t) / (rampa.horas * HORA)
    valor += rampa.variacao * Math.min(1, Math.max(0, progresso))
  }

  const fator = 10 ** p.casas
  return Math.round(Math.min(p.max, Math.max(p.min, valor)) * fator) / fator
}

export interface PontoGerado {
  ts: string
  valor: number
  min?: number
  max?: number
}

/** Gera a série entre `inicio` e `fim` (já recortados à disponibilidade de dados). */
export function gerarSerie(
  cenario: CenarioSerie,
  g: Grandeza,
  inicio: number,
  fim: number,
  passoMs: number,
  agora = Date.now(),
): PontoGerado[] {
  const pontos: PontoGerado[] = []
  const primeiro = Math.ceil(inicio / passoMs) * passoMs

  if (passoMs === MINUTO) {
    for (let t = primeiro; t <= fim; t += MINUTO) {
      pontos.push({ ts: new Date(t).toISOString(), valor: valorEm(cenario, g, t, agora) })
    }
    return pontos
  }

  // Agregação por janela (média, mínimo e máximo), como a visão materializada de médias horárias.
  const amostragem = Math.max(MINUTO, passoMs / 12)
  for (let janela = Math.floor(inicio / passoMs) * passoMs; janela <= fim; janela += passoMs) {
    const valores: number[] = []
    for (let t = Math.max(janela, inicio); t < janela + passoMs && t <= fim; t += amostragem) {
      valores.push(valorEm(cenario, g, t, agora))
    }
    if (valores.length === 0) continue
    const soma = valores.reduce((a, b) => a + b, 0)
    const casas = cenario.parametros[g].casas + 1
    const fator = 10 ** casas
    pontos.push({
      ts: new Date(janela).toISOString(),
      valor: Math.round((soma / valores.length) * fator) / fator,
      min: Math.min(...valores),
      max: Math.max(...valores),
    })
  }
  return pontos
}
