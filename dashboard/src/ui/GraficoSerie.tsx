import { useEffect, useRef, useState } from 'react'
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatarDataHora, formatarDiaMes, formatarHora, formatarNumero } from '@/compartilhado/formatacao'
import type { Grandeza } from '@/dominio/comum'
import { formatarValor, GRANDEZAS, type FaixaIdeal } from '@/dominio/grandezas'

export interface PontoGrafico {
  ts: number
  valor: number
}

export interface PropsGraficoSerie {
  grandeza: Grandeza
  rotulo: string
  pontos: PontoGrafico[]
  previsao?: PontoGrafico[]
  faixaIdeal?: FaixaIdeal | null
  inicio: number
  fim: number
  altura?: number
  formatoTempo: 'hora' | 'dia'
}

interface Linha {
  ts: number
  real?: number | null
  previsto?: number
}

/** Quebra a linha onde faltam leituras (ex.: nó sensor offline), em vez de ligar os pontos. */
function comLacunas(pontos: PontoGrafico[]): Linha[] {
  if (pontos.length < 3) return pontos.map((p) => ({ ts: p.ts, real: p.valor }))
  const passo = pontos[1]!.ts - pontos[0]!.ts
  const linhas: Linha[] = []
  pontos.forEach((ponto, i) => {
    const anterior = pontos[i - 1]
    if (anterior && ponto.ts - anterior.ts > passo * 3) linhas.push({ ts: anterior.ts + passo, real: null })
    linhas.push({ ts: ponto.ts, real: ponto.valor })
  })
  return linhas
}

function resumoAcessivel(rotulo: string, grandeza: Grandeza, pontos: PontoGrafico[]): string {
  const ultimo = pontos[pontos.length - 1]
  if (!ultimo) return `${rotulo}: sem leituras no período.`
  const valores = pontos.map((p) => p.valor)
  return (
    `${rotulo}: último valor ${formatarValor(grandeza, ultimo.valor)} em ${formatarDataHora(ultimo.ts)}; ` +
    `mínimo ${formatarValor(grandeza, Math.min(...valores))}; máximo ${formatarValor(grandeza, Math.max(...valores))}.`
  )
}

/**
 * Largura do contêiner medida aqui, e não pelo modo `responsive` do Recharts: se o gráfico monta
 * com a página sem área visível (aba em segundo plano), o Recharts fica preso na largura padrão.
 */
function useLargura() {
  const ref = useRef<HTMLDivElement>(null)
  const [largura, setLargura] = useState(0)
  useEffect(() => {
    const elemento = ref.current
    if (!elemento) return
    const observador = new ResizeObserver(([entrada]) =>
      setLargura(Math.floor(entrada?.contentRect.width ?? 0)),
    )
    observador.observe(elemento)
    return () => observador.disconnect()
  }, [])
  return [ref, largura] as const
}

export default function GraficoSerie({
  grandeza,
  rotulo,
  pontos,
  previsao = [],
  faixaIdeal,
  inicio,
  fim,
  altura = 180,
  formatoTempo,
}: PropsGraficoSerie) {
  const [ref, largura] = useLargura()
  const { cor, casas } = GRANDEZAS[grandeza]
  const ultimoReal = pontos[pontos.length - 1]
  const dados: Linha[] = [...comLacunas(pontos)]
  if (ultimoReal && previsao.length) {
    dados[dados.length - 1] = { ...dados[dados.length - 1]!, previsto: ultimoReal.valor }
    for (const p of previsao) dados.push({ ts: p.ts, previsto: p.valor })
  }

  const valores = [...pontos, ...previsao].map((p) => p.valor)
  if (faixaIdeal) valores.push(faixaIdeal.min, ...(faixaIdeal.max === null ? [] : [faixaIdeal.max]))
  const minimo = valores.length ? Math.min(...valores) : 0
  const maximo = valores.length ? Math.max(...valores) : 1
  const margem = Math.max((maximo - minimo) * 0.15, 10 ** -casas)
  const fimEixo = Math.max(fim, ...previsao.map((p) => p.ts))
  const formatarTempo = formatoTempo === 'hora' ? formatarHora : formatarDiaMes

  return (
    <div
      ref={ref}
      role="img"
      aria-label={resumoAcessivel(rotulo, grandeza, pontos)}
      style={{ height: altura }}
    >
      {largura > 0 && (
        <ComposedChart
          width={largura}
          height={altura}
          accessibilityLayer={false}
          data={dados}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="var(--color-borda)" vertical={false} />
          {faixaIdeal && (
            <ReferenceArea
              y1={faixaIdeal.min}
              // sem limite superior (OD), a faixa vai até o topo do gráfico
              y2={faixaIdeal.max ?? maximo + margem}
              fill="var(--color-otimo)"
              fillOpacity={0.08}
              stroke="none"
            />
          )}
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={[inicio, fimEixo]}
            tickFormatter={(t: number) => formatarTempo(t)}
            tick={{ fontSize: 12, fill: 'var(--color-tinta-suave)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--color-borda-forte)' }}
            minTickGap={24}
          />
          <YAxis
            domain={[minimo - margem, maximo + margem]}
            tickFormatter={(v: number) => formatarNumero(v, casas)}
            tick={{ fontSize: 12, fill: 'var(--color-tinta-suave)' }}
            tickLine={false}
            axisLine={false}
            width={44}
            tickCount={5}
          />
          <Tooltip
            isAnimationActive={false}
            // o padrão do Recharts é fundo branco fixo: com os tokens, o balão acompanha o tema
            contentStyle={{
              backgroundColor: 'var(--color-superficie)',
              border: '1px solid var(--color-borda)',
              borderRadius: 8,
              color: 'var(--color-tinta)',
            }}
            labelStyle={{ color: 'var(--color-tinta)', fontWeight: 600 }}
            cursor={{ stroke: 'var(--color-borda-forte)' }}
            labelFormatter={(t) => formatarDataHora(Number(t))}
            formatter={(valor, nome) => [
              formatarValor(grandeza, Number(valor)),
              nome === 'previsto' ? 'Previsão' : rotulo,
            ]}
          />
          {previsao.length > 0 && ultimoReal && (
            <ReferenceLine x={ultimoReal.ts} stroke="var(--color-neutro)" strokeDasharray="4 4" />
          )}
          <Line
            dataKey="real"
            stroke={cor}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            connectNulls={false}
          />
          {previsao.length > 0 && (
            <Line
              dataKey="previsto"
              stroke={cor}
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={{ r: 3, fill: cor }}
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      )}
    </div>
  )
}
