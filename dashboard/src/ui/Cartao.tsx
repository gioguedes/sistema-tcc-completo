import type { HTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'
import { ArrowRight } from 'lucide-react'
import { cn } from '@/compartilhado/cn'

export function Cartao({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={cn('rounded-xl border border-borda bg-superficie p-4 sm:p-5', className)} {...props} />
}

interface PropsCabecalho {
  titulo: ReactNode
  /** Nível do título dentro da página. */
  nivel?: 'h2' | 'h3'
  id?: string
  acao?: ReactNode
  link?: { para: string; texto: string }
  className?: string
}

/** "Cabeçalho de Cartão" do Figma: título à esquerda, link "Ver todos →" à direita. */
export function CabecalhoCartao({ titulo, nivel: Nivel = 'h2', id, acao, link, className }: PropsCabecalho) {
  return (
    <div className={cn('mb-4 flex flex-wrap items-center justify-between gap-2', className)}>
      <Nivel id={id} className="text-base font-semibold text-tinta sm:text-lg">
        {titulo}
      </Nivel>
      {acao}
      {link && <LinkSeta para={link.para}>{link.texto}</LinkSeta>}
    </div>
  )
}

export function LinkSeta({ para, children, className }: { para: string; children: ReactNode; className?: string }) {
  return (
    <Link
      to={para}
      className={cn(
        'inline-flex min-h-9 items-center gap-1 rounded text-sm font-semibold text-primaria hover:text-primaria-escura hover:underline pointer-coarse:min-h-11',
        className,
      )}
    >
      {children}
      <ArrowRight aria-hidden className="size-4" />
    </Link>
  )
}
