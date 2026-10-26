import { useEffect, useId, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { Botao } from './Botao'

interface PropsDialogo {
  aberto: boolean
  aoFechar: () => void
  titulo: string
  descricao?: ReactNode
  children?: ReactNode
  rodape?: ReactNode
}

/**
 * Usa o <dialog> nativo: foco preso no modal, Esc para fechar e fundo inerte
 * sem dependências extras. No celular ocupa a largura toda, ancorado embaixo.
 */
export function Dialogo({ aberto, aoFechar, titulo, descricao, children, rodape }: PropsDialogo) {
  const ref = useRef<HTMLDialogElement>(null)
  const idTitulo = useId()
  const idDescricao = useId()

  useEffect(() => {
    const dialogo = ref.current
    if (!dialogo) return
    if (aberto && !dialogo.open) dialogo.showModal?.()
    if (!aberto && dialogo.open) dialogo.close?.()
  }, [aberto])

  return (
    <dialog
      ref={ref}
      aria-labelledby={idTitulo}
      aria-describedby={descricao ? idDescricao : undefined}
      onCancel={(evento) => {
        evento.preventDefault()
        aoFechar()
      }}
      className="m-0 mt-auto w-full max-w-none rounded-t-2xl bg-superficie p-0 text-tinta shadow-xl sm:m-auto sm:max-w-lg sm:rounded-2xl"
    >
      {aberto && (
        <div className="flex max-h-[90dvh] flex-col">
          <div className="flex items-start justify-between gap-4 border-b border-borda px-5 py-4">
            <div>
              <h2 id={idTitulo} className="text-lg font-semibold">
                {titulo}
              </h2>
              {descricao && (
                <p id={idDescricao} className="mt-1 text-sm text-tinta-suave">
                  {descricao}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={aoFechar}
              aria-label="Fechar"
              className="-mr-2 flex size-11 shrink-0 items-center justify-center rounded-lg text-tinta-suave hover:bg-neutro-fundo"
            >
              <X aria-hidden className="size-5" />
            </button>
          </div>
          {children && <div className="overflow-y-auto px-5 py-4">{children}</div>}
          {rodape && (
            <div className="flex flex-col-reverse gap-2 border-t border-borda px-5 py-4 sm:flex-row sm:justify-end">
              {rodape}
            </div>
          )}
        </div>
      )}
    </dialog>
  )
}

interface PropsConfirmacao {
  aberto: boolean
  titulo: string
  descricao: ReactNode
  textoConfirmar: string
  perigo?: boolean
  carregando?: boolean
  aoConfirmar: () => void
  aoCancelar: () => void
}

export function DialogoConfirmacao({
  aberto,
  titulo,
  descricao,
  textoConfirmar,
  perigo,
  carregando,
  aoConfirmar,
  aoCancelar,
}: PropsConfirmacao) {
  return (
    <Dialogo
      aberto={aberto}
      aoFechar={aoCancelar}
      titulo={titulo}
      descricao={descricao}
      rodape={
        <>
          <Botao variante="secundario" onClick={aoCancelar} disabled={carregando}>
            Cancelar
          </Botao>
          <Botao variante={perigo ? 'perigo' : 'primario'} onClick={aoConfirmar} carregando={carregando}>
            {textoConfirmar}
          </Botao>
        </>
      }
    />
  )
}
