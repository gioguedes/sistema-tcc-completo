import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Link, type LinkProps } from 'react-router'
import { Loader2, type LucideIcon } from 'lucide-react'
import { cn } from '@/compartilhado/cn'

type Variante = 'primario' | 'perigo' | 'escuro' | 'secundario' | 'fantasma'
type Tamanho = 'md' | 'sm'

const VARIANTES: Record<Variante, string> = {
  primario: 'bg-primaria-solida text-white hover:bg-primaria-solida-hover',
  perigo: 'bg-critico-solido text-white hover:bg-critico-escuro',
  escuro: 'bg-marinho text-white hover:bg-marinho-escuro',
  secundario: 'border border-borda-forte bg-superficie text-tinta hover:bg-neutro-fundo',
  fantasma: 'text-primaria hover:bg-primaria-fundo',
}

const TAMANHOS: Record<Tamanho, string> = {
  md: 'min-h-11 px-4 text-sm',
  // compacto no mouse; no toque mantém os 44 px mínimos do TC2 (§8.4)
  sm: 'min-h-9 px-3 text-sm pointer-coarse:min-h-11',
}

interface OpcoesVisuais {
  variante?: Variante
  tamanho?: Tamanho
  larguraTotal?: boolean
}

export function classesBotao({ variante = 'primario', tamanho = 'md', larguraTotal }: OpcoesVisuais = {}) {
  return cn(
    'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors',
    'disabled:cursor-not-allowed disabled:opacity-60',
    VARIANTES[variante],
    TAMANHOS[tamanho],
    larguraTotal && 'w-full',
  )
}

interface PropsBotao extends ButtonHTMLAttributes<HTMLButtonElement>, OpcoesVisuais {
  icone?: LucideIcon
  carregando?: boolean
}

export const Botao = forwardRef<HTMLButtonElement, PropsBotao>(function Botao(
  { variante, tamanho, larguraTotal, icone: Icone, carregando, disabled, className, children, type = 'button', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || carregando}
      aria-busy={carregando || undefined}
      className={cn(classesBotao({ variante, tamanho, larguraTotal }), className)}
      {...props}
    >
      {carregando ? (
        <Loader2 aria-hidden className="size-4 animate-spin" />
      ) : (
        Icone && <Icone aria-hidden className="size-4" />
      )}
      {children}
    </button>
  )
})

interface PropsBotaoLink extends LinkProps, OpcoesVisuais {
  icone?: LucideIcon
}

export function BotaoLink({ variante, tamanho, larguraTotal, icone: Icone, className, children, ...props }: PropsBotaoLink) {
  return (
    <Link className={cn(classesBotao({ variante, tamanho, larguraTotal }), className)} {...props}>
      {Icone && <Icone aria-hidden className="size-4" />}
      {children}
    </Link>
  )
}
