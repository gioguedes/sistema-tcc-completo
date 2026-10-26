import type { ReactNode } from 'react'
import { AlertOctagon, AlertTriangle, CheckCircle2, CircleDashed, type LucideIcon } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import type { NivelRisco } from '@/dominio/comum'
import { ROTULO_RISCO } from '@/dominio/rotulos'

export type Tom = 'otimo' | 'atencao' | 'critico' | 'neutro' | 'info'

const TONS: Record<Tom, string> = {
  otimo: 'bg-otimo-fundo text-otimo',
  atencao: 'bg-atencao-fundo text-atencao',
  critico: 'bg-critico-solido text-white',
  neutro: 'bg-neutro-fundo text-tinta-suave',
  info: 'bg-primaria-fundo text-primaria-escura',
}

interface PropsEtiqueta {
  tom?: Tom
  icone?: LucideIcon
  ponto?: boolean
  children: ReactNode
  className?: string
}

export function Etiqueta({ tom = 'neutro', icone: Icone, ponto, children, className }: PropsEtiqueta) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap',
        TONS[tom],
        className,
      )}
    >
      {Icone && <Icone aria-hidden className="size-3.5" />}
      {ponto && !Icone && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}

const ICONE_RISCO: Record<NivelRisco, LucideIcon> = {
  otimo: CheckCircle2,
  atencao: AlertTriangle,
  critico: AlertOctagon,
}

/** Selo de risco: cor, ícone e texto juntos — a cor nunca é o único portador de significado. */
export function SeloRisco({ nivel, className }: { nivel: NivelRisco | null; className?: string }) {
  if (nivel === null) {
    return (
      <Etiqueta tom="neutro" icone={CircleDashed} className={className}>
        Sem previsão
      </Etiqueta>
    )
  }
  return (
    <Etiqueta tom={nivel} icone={ICONE_RISCO[nivel]} className={className}>
      {ROTULO_RISCO[nivel]}
    </Etiqueta>
  )
}

