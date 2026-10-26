import { useState } from 'react'
import { Fan, Power, PowerOff } from 'lucide-react'
import { tempoRelativo } from '@/compartilhado/formatacao'
import type { AcaoAtuador } from '@/dominio/comum'
import type { Dispositivo } from '@/dominio/entidades'
import { ehErroApi, mensagemDeErro } from '@/infra/api/erros'
import { Botao } from '@/ui/Botao'
import { DialogoConfirmacao } from '@/ui/Dialogo'
import { useToast } from '@/ui/Toast'
import { useComandarAerador } from '../consultas/monitoramento'
import { usePreferencias } from '../preferencias'

export const AVISO_OFFLINE = 'O nó sensor está offline. O aerador pode ser comandado quando ele voltar a enviar dados.'

/** Envia o comando (F-02) e avisa o resultado; a API publica no broker e o nó aciona o relé. */
export function useComandoAerador(tanqueNome: string) {
  const comando = useComandarAerador()
  const { mostrar } = useToast()

  const enviar = (idDispositivo: number, acao: AcaoAtuador, aoTerminar: () => void) =>
    comando.mutate(
      { idDispositivo, acao },
      {
        onSuccess: () => {
          aoTerminar()
          mostrar(`Comando enviado. O aerador do ${tanqueNome} deve ${acao} em instantes.`)
        },
        onError: (erro) => {
          aoTerminar()
          // 503: a API não conseguiu falar com o broker, então o comando não saiu
          const naoEnviado = ehErroApi(erro) && erro.status === 503
          mostrar(
            naoEnviado ? 'Não foi possível enviar o comando ao nó sensor. Tente novamente.' : mensagemDeErro(erro),
            'erro',
          )
        },
      },
    )

  return { enviar, enviando: comando.isPending }
}

interface PropsControleAerador {
  dispositivo: Dispositivo
  tanqueNome: string
  agora: number
}

/** Ligar e desligar o aerador do nó, com o último comando enviado. */
export function ControleAerador({ dispositivo, tanqueNome, agora }: PropsControleAerador) {
  const [confirmando, setConfirmando] = useState<AcaoAtuador | null>(null)
  const { enviar, enviando } = useComandoAerador(tanqueNome)
  const { modoAvancado } = usePreferencias()
  const offline = dispositivo.status_conexao !== 'online'
  const ultimo = dispositivo.ultimo_acionamento
  const idTitulo = `aerador-${dispositivo.id}`

  return (
    <div role="group" aria-labelledby={idTitulo} className="mt-3 rounded-lg border border-borda p-3">
      <p id={idTitulo} className="flex items-center gap-2 text-sm font-semibold">
        <Fan aria-hidden className="size-4 text-tinta-suave" />
        Aerador
      </p>
      <p className="mt-1 text-xs text-tinta-suave">
        {ultimo
          ? `Último comando: ${ultimo.acao}, ${tempoRelativo(ultimo.ts_acionamento, agora)}${ultimo.automatico ? ' (automático)' : ''}.`
          : 'Nenhum comando enviado ainda.'}
      </p>
      {modoAvancado && ultimo?.motivo && <p className="mt-0.5 text-xs text-tinta-suave">{ultimo.motivo}</p>}

      <div className="mt-2 grid grid-cols-2 gap-2">
        <Botao icone={Power} disabled={offline || enviando} onClick={() => setConfirmando('ligar')}>
          Ligar
        </Botao>
        <Botao variante="secundario" icone={PowerOff} disabled={offline || enviando} onClick={() => setConfirmando('desligar')}>
          Desligar
        </Botao>
      </div>
      {offline && <p className="mt-2 text-xs text-tinta-suave">{AVISO_OFFLINE}</p>}
      {modoAvancado && (
        <p className="mt-2 text-xs text-tinta-suave">O painel mostra o último comando enviado; o nó ainda não confirma o estado do relé.</p>
      )}

      <DialogoConfirmacao
        aberto={confirmando !== null}
        titulo={confirmando === 'desligar' ? 'Desligar o aerador?' : 'Ligar o aerador?'}
        descricao={`O comando será enviado ao ${dispositivo.nome} do ${tanqueNome}.`}
        textoConfirmar={confirmando === 'desligar' ? 'Desligar aerador' : 'Ligar aerador'}
        // desligar reduz a oxigenação: pede o destaque de ação arriscada
        perigo={confirmando === 'desligar'}
        carregando={enviando}
        aoConfirmar={() => confirmando && enviar(dispositivo.id, confirmando, () => setConfirmando(null))}
        aoCancelar={() => setConfirmando(null)}
      />
    </div>
  )
}
