import type { ReactNode } from 'react'
import { AlertCircle, AlertOctagon, AlertTriangle, CheckCircle2, Info, Loader2, RotateCw, type LucideIcon } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import { mensagemDeErro } from '@/infra/api/erros'
import { Botao } from './Botao'

type TomAviso = 'info' | 'otimo' | 'atencao' | 'critico' | 'neutro'

const ESTILO_AVISO: Record<TomAviso, { classes: string; icone: LucideIcon }> = {
  info: { classes: 'border-primaria/25 bg-primaria-fundo text-tinta', icone: Info },
  otimo: { classes: 'border-otimo-borda bg-otimo-fundo text-tinta', icone: CheckCircle2 },
  atencao: { classes: 'border-atencao-borda bg-atencao-fundo text-tinta', icone: AlertTriangle },
  critico: { classes: 'border-critico-borda bg-critico-fundo text-tinta', icone: AlertOctagon },
  neutro: { classes: 'border-borda bg-neutro-fundo text-tinta', icone: Info },
}

const COR_ICONE: Record<TomAviso, string> = {
  info: 'text-primaria',
  otimo: 'text-otimo',
  atencao: 'text-atencao',
  critico: 'text-critico',
  neutro: 'text-tinta-suave',
}

interface PropsAviso {
  tom?: TomAviso
  titulo?: ReactNode
  children?: ReactNode
  acao?: ReactNode
  icone?: LucideIcon
  /** Avisos urgentes são anunciados imediatamente por leitores de tela. */
  urgente?: boolean
  className?: string
}

export function Aviso({ tom = 'info', titulo, children, acao, icone, urgente, className }: PropsAviso) {
  const { classes, icone: IconePadrao } = ESTILO_AVISO[tom]
  const Icone = icone ?? IconePadrao
  return (
    <div
      role={urgente ? 'alert' : 'status'}
      className={cn('flex items-start gap-3 rounded-xl border p-3 sm:p-4', classes, className)}
    >
      <Icone aria-hidden className={cn('mt-0.5 size-5 shrink-0', COR_ICONE[tom])} />
      <div className="min-w-0 flex-1 text-sm">
        {titulo && <p className="font-semibold">{titulo}</p>}
        {children && <div className={cn(titulo ? 'mt-0.5' : undefined, 'text-tinta-suave')}>{children}</div>}
      </div>
      {acao && <div className="shrink-0">{acao}</div>}
    </div>
  )
}

interface PropsVazio {
  icone: LucideIcon
  titulo: string
  descricao?: ReactNode
  acao?: ReactNode
  className?: string
}

export function EstadoVazio({ icone: Icone, titulo, descricao, acao, className }: PropsVazio) {
  return (
    <div className={cn('flex flex-col items-center px-4 py-10 text-center', className)}>
      <span className="mb-3 flex size-12 items-center justify-center rounded-full bg-neutro-fundo">
        <Icone aria-hidden className="size-6 text-tinta-suave" />
      </span>
      <p className="font-semibold">{titulo}</p>
      {descricao && <p className="mt-1 max-w-sm text-sm text-tinta-suave">{descricao}</p>}
      {acao && <div className="mt-4">{acao}</div>}
    </div>
  )
}

interface PropsErro {
  erro: unknown
  aoTentarNovamente?: () => void
  className?: string
}

export function EstadoErro({ erro, aoTentarNovamente, className }: PropsErro) {
  return (
    <div role="alert" className={cn('flex flex-col items-center px-4 py-8 text-center', className)}>
      <span className="mb-3 flex size-12 items-center justify-center rounded-full bg-critico-fundo">
        <AlertCircle aria-hidden className="size-6 text-critico" />
      </span>
      <p className="font-semibold">Não foi possível carregar</p>
      <p className="mt-1 max-w-sm text-sm text-tinta-suave">{mensagemDeErro(erro)}</p>
      {aoTentarNovamente && (
        <Botao variante="secundario" tamanho="sm" icone={RotateCw} onClick={aoTentarNovamente} className="mt-4">
          Tentar novamente
        </Botao>
      )}
    </div>
  )
}

export function Carregando({ texto = 'Carregando…', className }: { texto?: string; className?: string }) {
  return (
    <div role="status" className={cn('flex items-center justify-center gap-2 py-10 text-sm text-tinta-suave', className)}>
      <Loader2 aria-hidden className="size-5 animate-spin" />
      {texto}
    </div>
  )
}

export function Esqueleto({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse rounded-lg bg-neutro-fundo', className)} />
}
