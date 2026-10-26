export const BASE_API = import.meta.env.VITE_API_URL || '/api/v1'
export const TEMPO_LIMITE_MS = 15_000

export type Parametros = Record<string, string | number | boolean | null | undefined>

export function montarUrl(caminho: string, parametros?: Parametros): string {
  const url = new URL(`${BASE_API}${caminho}`, window.location.origin)
  for (const [chave, valor] of Object.entries(parametros ?? {})) {
    if (valor !== undefined && valor !== null && valor !== '') url.searchParams.set(chave, String(valor))
  }
  return url.toString()
}
