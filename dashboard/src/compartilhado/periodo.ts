import type { Bucket } from '@/dominio/entidades'

export type ChavePeriodo = '24h' | '7d' | '30d'

export type Periodo = { tipo: 'relativo'; chave: ChavePeriodo } | { tipo: 'personalizado'; desde: string; ate: string }

const HORA = 3_600_000

const DURACAO: Record<ChavePeriodo, number> = {
  '24h': 24 * HORA,
  '7d': 7 * 24 * HORA,
  '30d': 30 * 24 * HORA,
}

export const OPCOES_PERIODO: { valor: ChavePeriodo; rotulo: string }[] = [
  { valor: '24h', rotulo: '24h' },
  { valor: '7d', rotulo: '7d' },
  { valor: '30d', rotulo: '30d' },
]

/** Datas do tipo "AAAA-MM-DD" interpretadas no fuso do navegador. */
function inicioDoDiaLocal(data: string): Date {
  const [ano, mes, dia] = data.split('-').map(Number)
  return new Date(ano!, mes! - 1, dia!)
}

export function resolverPeriodo(periodo: Periodo, agora = Date.now()): { desde: Date; ate: Date } {
  if (periodo.tipo === 'relativo') {
    return { desde: new Date(agora - DURACAO[periodo.chave]), ate: new Date(agora) }
  }
  const desde = inicioDoDiaLocal(periodo.desde)
  const fimDoDia = inicioDoDiaLocal(periodo.ate).getTime() + 24 * HORA - 1
  return { desde, ate: new Date(Math.min(fimDoDia, agora)) }
}

/**
 * Agregação pedida à API (RNF02): dados brutos só em janelas curtas;
 * 24 h em blocos de 5 min (~288 pontos); períodos longos em médias horárias.
 */
export function escolherBucket(desde: Date, ate: Date): Bucket {
  const duracao = ate.getTime() - desde.getTime()
  if (duracao <= 6 * HORA) return 'raw'
  if (duracao <= 48 * HORA) return '5m'
  return '1h'
}

export function formatoTempo(desde: Date, ate: Date): 'hora' | 'dia' {
  return ate.getTime() - desde.getTime() <= 48 * HORA ? 'hora' : 'dia'
}

export function chaveDoPeriodo(periodo: Periodo): string {
  return periodo.tipo === 'relativo' ? periodo.chave : `${periodo.desde}_${periodo.ate}`
}

export function rotuloDoPeriodo(periodo: Periodo): string {
  if (periodo.tipo === 'personalizado') {
    const [, mesDe, diaDe] = periodo.desde.split('-')
    const [, mesAte, diaAte] = periodo.ate.split('-')
    return `${diaDe}/${mesDe} a ${diaAte}/${mesAte}`
  }
  return { '24h': 'Últimas 24 horas', '7d': 'Últimos 7 dias', '30d': 'Últimos 30 dias' }[periodo.chave]
}

/** Lê o período dos parâmetros da URL (compartilhável e preservado ao voltar/avançar). */
export function periodoDaUrl(parametros: URLSearchParams): Periodo {
  const chave = parametros.get('periodo')
  const desde = parametros.get('desde')
  const ate = parametros.get('ate')
  if (chave === 'personalizado' && desde && ate && desde <= ate) return { tipo: 'personalizado', desde, ate }
  if (chave === '7d' || chave === '30d') return { tipo: 'relativo', chave }
  return { tipo: 'relativo', chave: '24h' }
}
