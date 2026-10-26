import { useState } from 'react'
import { LineChart } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import { formatoTempo, type Periodo } from '@/compartilhado/periodo'
import type { Grandeza } from '@/dominio/comum'
import type { Especie, PrevisaoAtual, RespostaLeituras, SerieLeituras, Tanque } from '@/dominio/entidades'
import { faixaIdealDe, formatarValor, GRANDEZAS, ORDEM_GRANDEZAS } from '@/dominio/grandezas'
import { Grafico, type PontoGrafico } from '@/ui/Grafico'
import { EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { useLeituras, usePrevisaoAtual } from '../consultas/monitoramento'
import { useRotuloGrandeza } from '../preferencias'
import { ExplicacaoOd, ICONE_GRANDEZA } from './Tanque'

const HORA = 3_600_000

export function pontosDaSerie(serie: SerieLeituras | undefined): PontoGrafico[] {
  return (serie?.pontos ?? []).map((p) => ({ ts: Date.parse(p.ts), valor: p.valor }))
}

/** Previsões de 1 a 3 h posicionadas no horário-alvo (momento da previsão + horizonte). */
export function pontosPrevisao(previsao: PrevisaoAtual | undefined, g: Grandeza): PontoGrafico[] {
  return (previsao?.horizontes ?? [])
    .filter((h) => h.parametro_critico === g)
    .sort((a, b) => a.horizonte_h - b.horizonte_h)
    .map((h) => ({ ts: Date.parse(h.ts_previsao) + h.horizonte_h * HORA, valor: h.valor_previsto }))
}

export interface ResumoSerie {
  minimo: number
  maximo: number
  media: number
  ultimo: number
}

export function resumirSerie(serie: SerieLeituras | undefined): ResumoSerie | null {
  const pontos = serie?.pontos ?? []
  if (pontos.length === 0) return null
  const valores = pontos.map((p) => p.valor)
  return {
    minimo: Math.min(...pontos.map((p) => p.min ?? p.valor)),
    maximo: Math.max(...pontos.map((p) => p.max ?? p.valor)),
    media: valores.reduce((a, b) => a + b, 0) / valores.length,
    ultimo: valores[valores.length - 1]!,
  }
}

function Legenda({ tracejada, faixa }: { tracejada?: boolean; faixa?: boolean }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-tinta-suave">
      <li className="flex items-center gap-1.5">
        <span aria-hidden className="h-0.5 w-5 bg-tinta-suave" /> Valores reais
      </li>
      {tracejada && (
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="w-5 border-t-2 border-dashed border-tinta-suave" /> Previsão (indicativa)
        </li>
      )}
      {faixa && (
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="h-3 w-5 rounded-sm bg-otimo/15" /> Faixa ideal da espécie
        </li>
      )}
    </ul>
  )
}

interface PropsGraficoQualidade {
  tanque: Tanque
  periodo: Periodo
  altura?: number
}

/**
 * Gráfico "Qualidade da água" da tela inicial. Mantém o cartão com legenda do Figma,
 * mas exibe uma grandeza por vez, cada uma na sua escala (pH 0–14, °C, NTU até 3000).
 */
export function GraficoQualidade({ tanque, periodo, altura = 220 }: PropsGraficoQualidade) {
  const leituras = useLeituras(tanque.id, periodo)
  const previsao = usePrevisaoAtual(tanque.id)
  const rotulo = useRotuloGrandeza()
  const [escolhida, setEscolhida] = useState<Grandeza | null>(null)

  const emRisco = previsao.data?.nivel_risco && previsao.data.nivel_risco !== 'otimo'
  const grandeza = escolhida ?? (emRisco ? previsao.data?.horizontes[0]?.parametro_critico : undefined) ?? 'temperatura'

  if (leituras.isPending) return <Esqueleto className="h-56 w-full" />
  if (leituras.isError) return <EstadoErro erro={leituras.error} aoTentarNovamente={() => void leituras.refetch()} />

  const resposta = leituras.data
  const inicio = Date.parse(resposta.desde)
  const fim = Date.parse(resposta.ate)
  const pontos = pontosDaSerie(resposta.series.find((s) => s.grandeza === grandeza))
  const previstos = periodo.tipo === 'relativo' ? pontosPrevisao(previsao.data, grandeza) : []
  const faixa = faixaIdealDe(grandeza, tanque.especie)

  if (resposta.series.every((s) => s.pontos.length === 0)) {
    return (
      <EstadoVazio
        icone={LineChart}
        titulo="Sem leituras no período"
        descricao="Os gráficos aparecem assim que o nó sensor enviar dados."
      />
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-[minmax(0,1fr)_14rem]">
      <div className="min-w-0">
        <Grafico
          grandeza={grandeza}
          rotulo={rotulo(grandeza)}
          pontos={pontos}
          previsao={previstos}
          faixaIdeal={faixa}
          inicio={inicio}
          fim={fim}
          altura={altura}
          formatoTempo={formatoTempo(new Date(inicio), new Date(fim))}
        />
        <Legenda tracejada={previstos.length > 0} faixa={Boolean(faixa)} />
      </div>
      <div role="group" aria-label="Grandeza exibida no gráfico" className="flex flex-col gap-1">
        {ORDEM_GRANDEZAS.map((g) => {
          const serie = resposta.series.find((s) => s.grandeza === g)
          const ultimo = serie?.pontos[serie.pontos.length - 1]
          const ativa = g === grandeza
          return (
            <button
              key={g}
              type="button"
              aria-pressed={ativa}
              onClick={() => setEscolhida(g)}
              className={cn(
                'flex min-h-11 items-center gap-2 rounded-lg px-2 py-1 text-left text-sm transition-colors',
                ativa ? 'bg-primaria-fundo ring-1 ring-primaria/30' : 'hover:bg-neutro-fundo',
              )}
            >
              <span aria-hidden className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: GRANDEZAS[g].cor }} />
              <span className="min-w-0 flex-1 leading-tight">{rotulo(g)}</span>
              <span className="font-semibold tabular-nums">{ultimo ? formatarValor(g, ultimo.valor) : '—'}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

interface PropsGraficosPorGrandeza {
  resposta: RespostaLeituras
  especie: Especie | null
  previsao?: PrevisaoAtual
  altura?: number
  mostrarResumo?: boolean
  className?: string
}

/** Um gráfico por grandeza, cada um com a faixa ideal da espécie ao fundo. */
export function GraficosPorGrandeza({ resposta, especie, previsao, altura = 170, mostrarResumo, className }: PropsGraficosPorGrandeza) {
  const rotulo = useRotuloGrandeza()
  const inicio = Date.parse(resposta.desde)
  const fim = Date.parse(resposta.ate)
  const formato = formatoTempo(new Date(inicio), new Date(fim))

  return (
    <div className={cn('grid grid-cols-1 gap-4 md:grid-cols-2', className)}>
      {ORDEM_GRANDEZAS.map((g) => {
        const serie = resposta.series.find((s) => s.grandeza === g)
        const resumo = resumirSerie(serie)
        const previstos = pontosPrevisao(previsao, g)
        const faixa = faixaIdealDe(g, especie)
        const Icone = ICONE_GRANDEZA[g]
        return (
          <section key={g} aria-label={rotulo(g)} className="rounded-xl border border-borda bg-superficie p-4 break-inside-avoid">
            <div className="mb-2 flex items-center justify-between gap-2">
              <h3 className="flex items-center gap-2 text-sm font-semibold">
                <Icone aria-hidden className="size-4" style={{ color: GRANDEZAS[g].cor }} />
                {rotulo(g)}
                {GRANDEZAS[g].estimado && <ExplicacaoOd />}
              </h3>
              {resumo && <span className="text-sm font-semibold tabular-nums">{formatarValor(g, resumo.ultimo)}</span>}
            </div>
            {resumo ? (
              <>
                <Grafico
                  grandeza={g}
                  rotulo={rotulo(g)}
                  pontos={pontosDaSerie(serie)}
                  previsao={previstos}
                  faixaIdeal={faixa}
                  inicio={inicio}
                  fim={fim}
                  altura={altura}
                  formatoTempo={formato}
                />
                <Legenda tracejada={previstos.length > 0} faixa={Boolean(faixa)} />
                {mostrarResumo && (
                  <dl className="mt-3 grid grid-cols-3 gap-2 border-t border-borda pt-3 text-center text-xs">
                    {(
                      [
                        ['Mínimo', resumo.minimo],
                        ['Média', resumo.media],
                        ['Máximo', resumo.maximo],
                      ] as const
                    ).map(([nome, valor]) => (
                      <div key={nome}>
                        <dt className="text-tinta-suave">{nome}</dt>
                        <dd className="font-semibold tabular-nums">{formatarValor(g, valor)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </>
            ) : (
              <p className="py-10 text-center text-sm text-tinta-suave">Sem leituras no período.</p>
            )}
          </section>
        )
      })}
    </div>
  )
}
