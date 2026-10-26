import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'
import { cn } from '@/compartilhado/cn'

type TipoToast = 'sucesso' | 'erro' | 'info'

interface Toast {
  id: number
  tipo: TipoToast
  mensagem: string
}

interface ContextoToast {
  mostrar: (mensagem: string, tipo?: TipoToast) => void
}

const Contexto = createContext<ContextoToast | null>(null)

const ESTILO: Record<TipoToast, { icone: typeof Info; cor: string }> = {
  sucesso: { icone: CheckCircle2, cor: 'text-otimo' },
  erro: { icone: AlertCircle, cor: 'text-critico' },
  info: { icone: Info, cor: 'text-primaria' },
}

const DURACAO_MS = 5000

export function ProvedorToast({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const proximoId = useRef(1)

  const remover = useCallback((id: number) => setToasts((lista) => lista.filter((t) => t.id !== id)), [])

  const mostrar = useCallback(
    (mensagem: string, tipo: TipoToast = 'sucesso') => {
      const id = proximoId.current++
      setToasts((lista) => [...lista.slice(-2), { id, tipo, mensagem }])
      window.setTimeout(() => remover(id), DURACAO_MS)
    },
    [remover],
  )

  const valor = useMemo(() => ({ mostrar }), [mostrar])

  return (
    <Contexto.Provider value={valor}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 lg:bottom-6 lg:items-end lg:px-6 print:hidden"
      >
        {toasts.map((toast) => {
          const { icone: Icone, cor } = ESTILO[toast.tipo]
          return (
            <div
              key={toast.id}
              role={toast.tipo === 'erro' ? 'alert' : 'status'}
              className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-borda bg-superficie p-3 shadow-lg"
            >
              <Icone aria-hidden className={cn('mt-0.5 size-5 shrink-0', cor)} />
              <p className="flex-1 text-sm">{toast.mensagem}</p>
              <button
                type="button"
                onClick={() => remover(toast.id)}
                aria-label="Fechar notificação"
                className="-m-1 flex size-8 items-center justify-center rounded text-tinta-suave hover:bg-neutro-fundo"
              >
                <X aria-hidden className="size-4" />
              </button>
            </div>
          )
        })}
      </div>
    </Contexto.Provider>
  )
}

export function useToast() {
  const contexto = useContext(Contexto)
  if (!contexto) throw new Error('useToast precisa estar dentro de <ProvedorToast>')
  return contexto
}
