import type { LeituraAtual, Tanque } from './entidades'
import { severidade } from './rotulos'

const MINUTO = 60_000
/** O nó publica a cada 60 s; 5 min sem leitura é o limite de "offline" do UC02. */
export const LIMITE_LEITURA_MS = 5 * MINUTO
/** O serviço de ML grava a cada 300 s e não grava quando faltam dados; 3 ciclos sem linha nova = desatualizado. */
export const LIMITE_PREVISAO_MS = 15 * MINUTO

/**
 * Grandeza que ficou para trás das outras: o firmware publica `null` para sensor em falha,
 * e a ingestão não grava nada para ela. O OD estimado acompanha o ciclo do ML, não o do nó.
 */
export function leituraAtrasada(leitura: LeituraAtual, ultimaLeituraDoTanque: string | null): boolean {
  if (!ultimaLeituraDoTanque) return false
  const atraso = Date.parse(ultimaLeituraDoTanque) - Date.parse(leitura.ts)
  return atraso > (leitura.estimado ? LIMITE_PREVISAO_MS : LIMITE_LEITURA_MS)
}

export type SituacaoDados =
  | { tipo: 'sem_dispositivo' }
  | { tipo: 'aguardando' }
  | { tipo: 'online'; ultimaLeitura: string }
  | { tipo: 'offline'; ultimaLeitura: string | null }

/**
 * Situação do fluxo de dados do tanque. O status online/offline de cada nó
 * vem calculado da API (regra de 5 min do UC02); aqui só se combina.
 */
export function situacaoDados(tanque: Tanque): SituacaoDados {
  if (tanque.dispositivos.length === 0) return { tipo: 'sem_dispositivo' }
  if (tanque.dispositivos.some((d) => d.status_conexao === 'online') && tanque.ultima_leitura_em) {
    return { tipo: 'online', ultimaLeitura: tanque.ultima_leitura_em }
  }
  if (!tanque.ultima_leitura_em) return { tipo: 'aguardando' }
  return { tipo: 'offline', ultimaLeitura: tanque.ultima_leitura_em }
}

/** Mais urgentes primeiro (crítico, atenção, ótimo, sem previsão); empate por nome. */
export function ordenarPorUrgencia(tanques: Tanque[]): Tanque[] {
  return [...tanques].sort(
    (a, b) => severidade(b.nivel_risco) - severidade(a.nivel_risco) || a.nome.localeCompare(b.nome, 'pt-BR'),
  )
}

/**
 * Por que o serviço de ML não gerou previsão para o tanque: ele só roda para tanques `ativo`
 * com espécie, e não grava quando faltam leituras recentes de pH e temperatura.
 */
export function motivoSemPrevisao(tanque: Tanque): string {
  if (tanque.status !== 'ativo') return 'A previsão só é gerada para tanques ativos.'
  if (!tanque.especie) return 'Informe a espécie do tanque: a previsão usa as faixas ideais dela.'
  const situacao = situacaoDados(tanque)
  if (situacao.tipo === 'sem_dispositivo') return 'Cadastre um dispositivo para começar a receber leituras.'
  if (situacao.tipo !== 'online') return 'Sem leituras recentes do nó sensor para calcular a previsão.'
  return 'Coletando dados. A previsão aparece quando houver leituras suficientes.'
}
