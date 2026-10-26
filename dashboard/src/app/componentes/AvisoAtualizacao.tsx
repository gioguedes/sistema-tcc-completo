import { RefreshCw } from 'lucide-react'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { Botao } from '@/ui/Botao'

const UMA_HORA_MS = 60 * 60_000

/**
 * Registra o service worker e avisa quando há versão nova. A troca espera o "Atualizar":
 * recarregar sozinho poderia apagar um cadastro pela metade.
 */
export default function AvisoAtualizacao() {
  const {
    needRefresh: [novaVersao, setNovaVersao],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registro) {
      // painel que fica aberto o dia todo (ex.: num monitor) também recebe as atualizações
      if (registro) window.setInterval(() => void registro.update(), UMA_HORA_MS)
    },
  })

  if (!novaVersao) return null
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex justify-center px-4 lg:bottom-6 lg:justify-end lg:px-6 print:hidden">
      <div role="status" className="pointer-events-auto w-full max-w-sm rounded-xl border border-borda bg-superficie p-3 shadow-lg">
        <p className="flex items-start gap-3 text-sm">
          <RefreshCw aria-hidden className="mt-0.5 size-5 shrink-0 text-primaria" />
          Há uma nova versão do Painel Aquícola.
        </p>
        <div className="mt-3 flex justify-end gap-2">
          <Botao variante="secundario" tamanho="sm" onClick={() => setNovaVersao(false)}>
            Depois
          </Botao>
          <Botao tamanho="sm" onClick={() => void updateServiceWorker(true)}>
            Atualizar
          </Botao>
        </div>
      </div>
    </div>
  )
}
