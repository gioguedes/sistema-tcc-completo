import { forwardRef, useId, useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react'
import { Eye, EyeOff, Search } from 'lucide-react'
import { cn } from '@/compartilhado/cn'

const classeControle = (erro?: string) =>
  cn(
    'block w-full rounded-lg border bg-superficie px-3 text-base text-tinta placeholder:text-tinta-suave/70 sm:text-sm',
    'min-h-11 disabled:bg-neutro-fundo disabled:text-tinta-suave',
    erro ? 'border-critico' : 'border-borda-campo',
  )

interface PropsEnvelope {
  id: string
  rotulo: string
  dica?: string
  erro?: string
  obrigatorio?: boolean
  children: ReactNode
  className?: string
}

/** Rótulo, dica e mensagem de erro ligados ao controle por aria-describedby. */
function Envelope({ id, rotulo, dica, erro, obrigatorio, children, className }: PropsEnvelope) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={id} className="text-sm font-semibold text-tinta">
        {rotulo}
        {obrigatorio && (
          <span aria-hidden className="text-critico">
            {' '}
            *
          </span>
        )}
      </label>
      {children}
      {dica && !erro && (
        <p id={`${id}-dica`} className="text-xs text-tinta-suave">
          {dica}
        </p>
      )}
      {erro && (
        <p id={`${id}-erro`} className="text-xs font-semibold text-critico">
          {erro}
        </p>
      )}
    </div>
  )
}

const descricao = (id: string, dica?: string, erro?: string) => (erro ? `${id}-erro` : dica ? `${id}-dica` : undefined)

interface PropsCampo extends InputHTMLAttributes<HTMLInputElement> {
  rotulo: string
  dica?: string
  erro?: string
  obrigatorio?: boolean
  sufixo?: string
}

export const Campo = forwardRef<HTMLInputElement, PropsCampo>(function Campo(
  { rotulo, dica, erro, obrigatorio, sufixo, className, id: idExterno, ...props },
  ref,
) {
  const idGerado = useId()
  const id = idExterno ?? idGerado
  return (
    <Envelope id={id} rotulo={rotulo} dica={dica} erro={erro} obrigatorio={obrigatorio} className={className}>
      <div className="relative">
        <input
          ref={ref}
          id={id}
          aria-invalid={erro ? true : undefined}
          aria-describedby={descricao(id, dica, erro)}
          aria-required={obrigatorio || undefined}
          className={cn(classeControle(erro), sufixo && 'pr-12')}
          {...props}
        />
        {sufixo && (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-tinta-suave">
            {sufixo}
          </span>
        )}
      </div>
    </Envelope>
  )
})

export const CampoSenha = forwardRef<HTMLInputElement, Omit<PropsCampo, 'type' | 'sufixo'>>(function CampoSenha(
  { rotulo, dica, erro, obrigatorio, className, id: idExterno, ...props },
  ref,
) {
  const idGerado = useId()
  const id = idExterno ?? idGerado
  const [visivel, setVisivel] = useState(false)
  const Icone = visivel ? EyeOff : Eye
  return (
    <Envelope id={id} rotulo={rotulo} dica={dica} erro={erro} obrigatorio={obrigatorio} className={className}>
      <div className="relative">
        <input
          ref={ref}
          id={id}
          type={visivel ? 'text' : 'password'}
          aria-invalid={erro ? true : undefined}
          aria-describedby={descricao(id, dica, erro)}
          className={cn(classeControle(erro), 'pr-12')}
          {...props}
        />
        <button
          type="button"
          onClick={() => setVisivel((v) => !v)}
          aria-label={visivel ? 'Ocultar senha' : 'Mostrar senha'}
          aria-pressed={visivel}
          className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-tinta-suave hover:text-tinta"
        >
          <Icone aria-hidden className="size-5" />
        </button>
      </div>
    </Envelope>
  )
})

interface PropsSelecao extends SelectHTMLAttributes<HTMLSelectElement> {
  rotulo: string
  dica?: string
  erro?: string
  obrigatorio?: boolean
}

export const Selecao = forwardRef<HTMLSelectElement, PropsSelecao>(function Selecao(
  { rotulo, dica, erro, obrigatorio, className, id: idExterno, children, ...props },
  ref,
) {
  const idGerado = useId()
  const id = idExterno ?? idGerado
  return (
    <Envelope id={id} rotulo={rotulo} dica={dica} erro={erro} obrigatorio={obrigatorio} className={className}>
      <select
        ref={ref}
        id={id}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descricao(id, dica, erro)}
        aria-required={obrigatorio || undefined}
        className={classeControle(erro)}
        {...props}
      >
        {children}
      </select>
    </Envelope>
  )
})

interface PropsCaixa extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  rotulo: string
  descricao?: string
}

export const CaixaSelecao = forwardRef<HTMLInputElement, PropsCaixa>(function CaixaSelecao(
  { rotulo, descricao: texto, className, id: idExterno, ...props },
  ref,
) {
  const idGerado = useId()
  const id = idExterno ?? idGerado
  return (
    <div className={cn('flex items-start gap-3', className)}>
      <input
        ref={ref}
        id={id}
        type="checkbox"
        className="mt-0.5 size-5 shrink-0 rounded border-borda-campo accent-primaria"
        aria-describedby={texto ? `${id}-descricao` : undefined}
        {...props}
      />
      <div>
        <label htmlFor={id} className="text-sm font-semibold">
          {rotulo}
        </label>
        {texto && (
          <p id={`${id}-descricao`} className="text-xs text-tinta-suave">
            {texto}
          </p>
        )}
      </div>
    </div>
  )
})

interface PropsBusca extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  rotulo: string
}

export function CampoBusca({ rotulo, className, ...props }: PropsBusca) {
  return (
    <div className={cn('relative', className)}>
      <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-tinta-suave" />
      <input type="search" aria-label={rotulo} className={cn(classeControle(), 'pl-9')} {...props} />
    </div>
  )
}

interface PropsAlternador {
  rotulo: string
  descricao?: string
  ligado: boolean
  aoAlternar: (ligado: boolean) => void
}

/** Interruptor acessível (role="switch"), como os de "Ajustes" no Figma. */
export function Alternador({ rotulo, descricao: texto, ligado, aoAlternar }: PropsAlternador) {
  const id = useId()
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p id={`${id}-rotulo`} className="text-sm font-semibold">
          {rotulo}
        </p>
        {texto && (
          <p id={`${id}-descricao`} className="text-xs text-tinta-suave">
            {texto}
          </p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={ligado}
        aria-labelledby={`${id}-rotulo`}
        aria-describedby={texto ? `${id}-descricao` : undefined}
        onClick={() => aoAlternar(!ligado)}
        className={cn(
          // o ::before amplia a área de toque para 44 px de altura sem mudar o desenho
          "relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors before:absolute before:-inset-2 before:content-['']",
          ligado ? 'bg-primaria-solida' : 'bg-borda-campo',
        )}
      >
        <span
          aria-hidden
          className={cn(
            'inline-block size-5 rounded-full bg-white shadow transition-transform',
            ligado ? 'translate-x-6' : 'translate-x-1',
          )}
        />
      </button>
    </div>
  )
}
