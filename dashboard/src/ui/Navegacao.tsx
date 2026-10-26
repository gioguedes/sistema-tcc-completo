import type React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import { Botao } from './Botao'

interface PropsPaginacao {
  pagina: number
  total: number
  porPagina: number
  aoMudar: (pagina: number) => void
}

export function Paginacao({ pagina, total, porPagina, aoMudar }: PropsPaginacao) {
  const totalPaginas = Math.max(1, Math.ceil(total / porPagina))
  if (totalPaginas <= 1) return null
  return (
    <nav aria-label="Paginação" className="mt-4 flex items-center justify-between gap-2">
      <Botao
        variante="secundario"
        tamanho="sm"
        icone={ChevronLeft}
        disabled={pagina <= 1}
        onClick={() => aoMudar(pagina - 1)}
      >
        Anterior
      </Botao>
      <p className="text-sm text-tinta-suave" aria-live="polite">
        Página {pagina} de {totalPaginas}
      </p>
      <Botao
        variante="secundario"
        tamanho="sm"
        disabled={pagina >= totalPaginas}
        onClick={() => aoMudar(pagina + 1)}
      >
        Próxima
        <ChevronRight aria-hidden className="size-4" />
      </Botao>
    </nav>
  )
}

interface Opcao<T extends string> {
  valor: T
  rotulo: string
}

interface PropsSeletor<T extends string> {
  rotulo: string
  opcoes: Opcao<T>[]
  valor: T
  aoMudar: (valor: T, evento: React.MouseEvent<HTMLButtonElement>) => void
  className?: string
}

/** "Chip" de período do Figma (24h · 7d · 30d · Personalizado). */
export function SeletorSegmentado<T extends string>({ rotulo, opcoes, valor, aoMudar, className }: PropsSeletor<T>) {
  return (
    <div
      role="group"
      aria-label={rotulo}
      className={cn('inline-flex max-w-full overflow-x-auto rounded-lg bg-neutro-fundo p-1', className)}
    >
      {opcoes.map((opcao) => {
        const ativo = opcao.valor === valor
        return (
          <button
            key={opcao.valor}
            type="button"
            aria-pressed={ativo}
            onClick={(evento) => aoMudar(opcao.valor, evento)}
            className={cn(
              'min-h-9 rounded-md px-3 text-sm font-semibold whitespace-nowrap transition-colors pointer-coarse:min-h-11',
              ativo ? 'bg-superficie text-tinta shadow-sm' : 'text-tinta-suave hover:text-tinta',
            )}
          >
            {opcao.rotulo}
          </button>
        )
      })}
    </div>
  )
}
