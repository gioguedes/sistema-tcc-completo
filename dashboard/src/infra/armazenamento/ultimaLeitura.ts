import { del, get, set } from 'idb-keyval'
import { z } from 'zod'
import { tanque, type Tanque } from '@/dominio/entidades'

/**
 * Última leitura conhecida de cada tanque, guardada no IndexedDB (TC2 §9) para o painel abrir sem rede.
 * É uma cópia da lista de tanques: valores, horário de cada medição e o nível de risco daquele momento.
 */
export interface CopiaLocal {
  salvoEm: number
  tanques: Tanque[]
}

const CHAVE = 'painel-aquicola:ultima-leitura'
const copiaLocal = z.object({ salvoEm: z.number(), tanques: z.array(tanque) })

export async function salvarUltimaLeitura(tanques: Tanque[]): Promise<void> {
  try {
    await set(CHAVE, { salvoEm: Date.now(), tanques } satisfies CopiaLocal)
  } catch {
    // sem IndexedDB (aba anônima em alguns navegadores): o painel só não abre offline
  }
}

/** Devolve nada se a cópia não existir ou for de uma versão com outro formato. */
export async function lerUltimaLeitura(): Promise<CopiaLocal | null> {
  try {
    const resultado = copiaLocal.safeParse(await get(CHAVE))
    return resultado.success ? resultado.data : null
  } catch {
    return null
  }
}

/**
 * Ao sair ou perder a sessão, apaga a cópia e as respostas da API guardadas pelo service worker,
 * para outra pessoa no mesmo aparelho não ver os tanques da conta anterior.
 */
export async function apagarDadosLocais(): Promise<void> {
  try {
    await del(CHAVE)
  } catch {
    // nada salvo
  }
  if (typeof caches === 'undefined') return
  try {
    const nomes = await caches.keys()
    await Promise.all(nomes.filter((nome) => nome.startsWith('api-')).map((nome) => caches.delete(nome)))
  } catch {
    // Cache Storage indisponível
  }
}
