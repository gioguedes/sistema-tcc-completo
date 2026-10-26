import { AlertOctagon, AlertTriangle, CheckCircle2, CircleDashed, type LucideIcon } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import { formatarHora, formatarNumero } from '@/compartilhado/formatacao'
import { useAgora } from '@/compartilhado/hooks'
import type { PrevisaoAtual, Tanque } from '@/dominio/entidades'
import { motivoSemPrevisao } from '@/dominio/situacao'
import { formatarValor } from '@/dominio/grandezas'
import { montarVeredito, type Veredito } from '@/dominio/veredito'
import { Esqueleto } from '@/ui/Estados'
import { Etiqueta, SeloRisco } from '@/ui/Selos'
import { usePreferencias, useRotuloGrandeza } from '../preferencias'

const ESTILO: Record<Veredito['tom'], { classes: string; cor: string; icone: LucideIcon }> = {
  otimo: { classes: 'border-otimo-borda bg-otimo-fundo', cor: 'text-otimo', icone: CheckCircle2 },
  atencao: { classes: 'border-atencao-borda bg-atencao-fundo', cor: 'text-atencao', icone: AlertTriangle },
  critico: { classes: 'border-critico-borda bg-critico-fundo', cor: 'text-critico', icone: AlertOctagon },
  indeterminado: { classes: 'border-borda bg-neutro-fundo', cor: 'text-tinta-suave', icone: CircleDashed },
}

/** Faixa de veredito: o topo do painel é uma frase direta, não um número (RNF06). */
interface PropsVeredito {
  previsao: PrevisaoAtual | undefined
  tanque: Tanque
  carregando?: boolean
  /** Tela de um tanque só: veredito maior. Em listas (vários tanques) fica em 20 px. */
  destaque?: boolean
}

export function CartaoVeredito({ previsao, tanque, carregando, destaque }: PropsVeredito) {
  const rotulo = useRotuloGrandeza()
  const { modoAvancado } = usePreferencias()
  const agora = useAgora()
  if (carregando) return <Esqueleto className="h-24" />
  const veredito = montarVeredito(previsao, rotulo, agora, motivoSemPrevisao(tanque))
  const { classes, cor, icone: Icone } = ESTILO[veredito.tom]
  return (
    <section
      aria-label="Situação prevista"
      aria-live="polite"
      className={cn('flex gap-3 rounded-xl border p-4 transition-colors duration-[400ms]', classes)}
    >
      <Icone aria-hidden className={cn('mt-0.5 size-6 shrink-0', cor)} />
      <div className="min-w-0">
        {/* TC2 §8.2: veredito em peso 800 (40 px no TC2; 28/20 px aqui, porque o veredito é uma frase e não cabe em 40 px no celular) */}
        <p className={cn('font-extrabold', destaque ? 'text-2xl' : 'text-lg', cor)}>{veredito.titulo}</p>
        <p className="text-sm text-tinta-suave">{veredito.detalhe}</p>
        <div className="mt-2 flex flex-wrap gap-2 empty:hidden">
          {veredito.baixaConfianca && <Etiqueta tom="neutro">Confiança baixa</Etiqueta>}
          {modoAvancado && previsao?.gerada_em && (
            <span className="text-xs text-tinta-suave">Previsão gerada às {formatarHora(previsao.gerada_em)}</span>
          )}
        </div>
      </div>
    </section>
  )
}

/** "Previsão de risco": OD estimado agora (h = 0) e nível previsto para 1, 2 e 3 horas (RF05). */
export function PrevisaoPorHorizonte({ previsao }: { previsao: PrevisaoAtual | undefined }) {
  const rotulo = useRotuloGrandeza()
  const { modoAvancado } = usePreferencias()
  const horizontes = [...(previsao?.horizontes ?? [])].sort((a, b) => a.horizonte_h - b.horizonte_h)
  const od = previsao?.od_atual
  if (horizontes.length === 0 && !od) {
    return null
  }
  const percentual = (valor: number) => `${formatarNumero(valor * 100, 0)}%`
  return (
    <div>
      <ul className="divide-y divide-borda">
        {od && (
          <li className="flex flex-wrap items-center justify-between gap-2 py-2">
            <div>
              <p className="text-sm font-semibold">Agora</p>
              <p className="text-xs text-tinta-suave">
                {rotulo('od')}: {formatarValor('od', od.valor)}
                {modoAvancado && od.confianca !== null && ` · confiança ${percentual(od.confianca)}`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {od.baixa_confianca && <Etiqueta tom="neutro">Confiança baixa</Etiqueta>}
              <SeloRisco nivel={od.nivel_risco} />
            </div>
          </li>
        )}
        {horizontes.map((h) => (
          <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <div>
              <p className="text-sm font-semibold">Em {h.horizonte_h === 1 ? '1 hora' : `${h.horizonte_h} horas`}</p>
              <p className="text-xs text-tinta-suave">
                {rotulo(h.parametro_critico)}: ≈ {formatarValor(h.parametro_critico, h.valor_previsto)}
                {modoAvancado && h.confianca !== null && ` · probabilidade ${percentual(h.confianca)}`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {h.baixa_confianca && <Etiqueta tom="neutro">Confiança baixa</Etiqueta>}
              <SeloRisco nivel={h.nivel_risco} />
            </div>
          </li>
        ))}
      </ul>
      {modoAvancado && horizontes.length > 0 && (
        <p className="mt-2 text-xs text-tinta-suave">
          O nível de cada horizonte vem do modelo de Machine Learning. O valor com “≈” é uma projeção indicativa da
          grandeza mais perto de sair da faixa.
        </p>
      )}
    </div>
  )
}
