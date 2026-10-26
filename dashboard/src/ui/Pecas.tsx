import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Info, type LucideIcon } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import type { Tom } from './Selos'

const TOM_INDICADOR: Record<Exclude<Tom, 'neutro'>, string> = {
  otimo: 'border-otimo-borda bg-otimo-fundo text-otimo',
  atencao: 'border-atencao-borda bg-atencao-fundo text-atencao',
  critico: 'border-critico-borda bg-critico-fundo text-critico',
  info: 'border-primaria/20 bg-primaria-fundo text-primaria',
}

interface PropsIndicador {
  tom: Exclude<Tom, 'neutro'>
  icone: LucideIcon
  rotulo: string
  valor: number
  detalhe?: string
}

/** "Cartão de Indicador" do Figma: contagem de tanques por situação. */
export function CartaoIndicador({ tom, icone: Icone, rotulo, valor, detalhe }: PropsIndicador) {
  return (
    <div className={cn('rounded-xl border p-3 sm:p-4', TOM_INDICADOR[tom])}>
      <p className="flex items-center gap-1.5 text-xs font-semibold sm:text-sm">
        <Icone aria-hidden className="size-4" />
        {rotulo}
      </p>
      <p className="mt-1 text-2xl font-extrabold text-tinta tabular-nums sm:text-3xl">{valor}</p>
      {detalhe && <p className="text-xs text-tinta-suave">{detalhe}</p>}
    </div>
  )
}

interface PropsLinhaMetrica {
  icone: LucideIcon
  rotulo: ReactNode
  valor: ReactNode
  complemento?: ReactNode
  atenuado?: boolean
}

/** "Linha de Métrica" do Figma: ícone, rótulo e valor alinhado à direita. */
export function LinhaMetrica({ icone: Icone, rotulo, valor, complemento, atenuado }: PropsLinhaMetrica) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-neutro-fundo text-tinta-suave">
        <Icone aria-hidden className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-tinta-suave">{rotulo}</p>
        {complemento && <p className="text-xs text-tinta-suave">{complemento}</p>}
      </div>
      <p className={cn('shrink-0 text-sm font-semibold whitespace-nowrap tabular-nums', atenuado && 'text-tinta-suave')}>{valor}</p>
    </div>
  )
}

interface PropsItemEvento {
  cor: string
  momento: string
  titulo: ReactNode
  descricao?: ReactNode
}

/** "Item de Evento" do Figma: ponto colorido, horário, título e descrição. */
export function ItemEvento({ cor, momento, titulo, descricao }: PropsItemEvento) {
  return (
    <li className="flex gap-3 py-2">
      <span aria-hidden className={cn('mt-1.5 size-2.5 shrink-0 rounded-full', cor)} />
      <span className="w-16 shrink-0 pt-px text-xs text-tinta-suave tabular-nums">{momento}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{titulo}</p>
        {descricao && <p className="text-xs text-tinta-suave">{descricao}</p>}
      </div>
    </li>
  )
}

interface PropsInfo {
  rotulo: string
  children: ReactNode
  className?: string
}

/** Explicação acessível ao toque (não depende de passar o mouse). */
export function InfoPopover({ rotulo, children, className }: PropsInfo) {
  const [aberto, setAberto] = useState(false)
  const id = useId()
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!aberto) return
    const fecharFora = (evento: PointerEvent) => {
      if (!ref.current?.contains(evento.target as Node)) setAberto(false)
    }
    const fecharEsc = (evento: KeyboardEvent) => evento.key === 'Escape' && setAberto(false)
    document.addEventListener('pointerdown', fecharFora)
    document.addEventListener('keydown', fecharEsc)
    return () => {
      document.removeEventListener('pointerdown', fecharFora)
      document.removeEventListener('keydown', fecharEsc)
    }
  }, [aberto])

  return (
    <span ref={ref} className={cn('relative inline-flex', className)}>
      <button
        type="button"
        aria-label={rotulo}
        aria-expanded={aberto}
        aria-controls={id}
        onClick={() => setAberto((a) => !a)}
        className="-m-2 flex size-9 shrink-0 items-center justify-center rounded-full text-tinta-suave hover:text-primaria pointer-coarse:size-11"
      >
        <Info aria-hidden className="size-4" />
      </button>
      {aberto && (
        <span
          id={id}
          role="note"
          className="absolute top-full right-0 z-20 mt-1 w-64 rounded-lg border border-borda bg-superficie p-3 text-left text-xs font-normal text-tinta shadow-lg"
        >
          {children}
        </span>
      )}
    </span>
  )
}

/** Ilustração do Figma (água com peixes), tingida conforme o risco. Puramente decorativa. */
export function IlustracaoTanque({ critico, className }: { critico?: boolean; className?: string }) {
  // tokens do index.css: a ilustração acompanha o tema claro/escuro
  const agua = critico ? 'var(--color-ilustracao-agua-critica)' : 'var(--color-ilustracao-agua)'
  const peixe = critico ? 'var(--color-ilustracao-peixe-critico)' : 'var(--color-ilustracao-peixe)'
  const peixes = [
    [40, 34],
    [92, 26],
    [130, 40],
    [70, 50],
    [160, 28],
  ]
  return (
    <svg aria-hidden viewBox="0 0 200 64" preserveAspectRatio="none" className={cn('h-16 w-full rounded-lg', className)}>
      <rect width="200" height="64" rx="8" fill={agua} />
      <path d="M0 10 Q 12.5 4 25 10 T 50 10 T 75 10 T 100 10 T 125 10 T 150 10 T 175 10 T 200 10" fill="none" stroke="var(--color-ilustracao-onda)" strokeWidth="2" />
      {peixes.map(([x, y]) => (
        <g key={`${x}-${y}`} transform={`translate(${x} ${y})`} fill="none" stroke={peixe} strokeWidth="1.4">
          <ellipse cx="0" cy="0" rx="8" ry="4" />
          <path d="M8 0 L13 -4 L13 4 Z" />
        </g>
      ))}
    </svg>
  )
}
