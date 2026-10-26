import { lazy, Suspense } from 'react'
import type { PropsGraficoSerie } from './GraficoSerie'
import { Esqueleto } from './Estados'

// O Recharts só é baixado quando um gráfico aparece na tela (RNF02: carregamento inicial enxuto).
const GraficoSerie = lazy(() => import('./GraficoSerie'))

export function Grafico(props: PropsGraficoSerie) {
  return (
    <Suspense
      fallback={
        <div style={{ height: props.altura ?? 180 }}>
          <Esqueleto className="size-full" />
        </div>
      }
    >
      <GraficoSerie {...props} />
    </Suspense>
  )
}

export type { PontoGrafico } from './GraficoSerie'
