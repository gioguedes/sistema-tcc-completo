import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Cpu, Pencil, Plus } from 'lucide-react'
import { tempoRelativo } from '@/compartilhado/formatacao'
import type { StatusSensor } from '@/dominio/comum'
import type { Dispositivo } from '@/dominio/entidades'
import { esquemaDispositivo, type EntradaDispositivo, type ValoresDispositivo } from '@/dominio/formularios'
import { rotuloGrandeza } from '@/dominio/grandezas'
import { ROTULO_CONEXAO, ROTULO_STATUS_SENSOR } from '@/dominio/rotulos'
import { mensagemDeErro } from '@/infra/api/erros'
import { Botao } from '@/ui/Botao'
import { CabecalhoCartao, Cartao } from '@/ui/Cartao'
import { Dialogo } from '@/ui/Dialogo'
import { Aviso, EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { Etiqueta } from '@/ui/Selos'
import { useToast } from '@/ui/Toast'
import { aplicarErrosDaApi, paraDadosDispositivo } from '../../componentes/formularios'
import { useAtualizarDispositivo, useAtualizarSensor, useCriarDispositivo, useDispositivos } from '../../consultas/tanques'
import { CamposDispositivo, DISPOSITIVO_VAZIO } from './CamposDispositivo'

interface PropsDialogo {
  idTanque: number
  dispositivo: Dispositivo | null
  aoFechar: () => void
}

function DialogoDispositivo({ idTanque, dispositivo, aoFechar }: PropsDialogo) {
  const criar = useCriarDispositivo(idTanque)
  const atualizar = useAtualizarDispositivo()
  const { mostrar } = useToast()
  const [erroGeral, setErroGeral] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<EntradaDispositivo, unknown, ValoresDispositivo>({
    resolver: zodResolver(esquemaDispositivo),
    defaultValues: dispositivo
      ? {
          nome: dispositivo.nome,
          mac_address: dispositivo.mac_address.toUpperCase(),
          modelo_esp32: dispositivo.modelo_esp32,
          versao_firmware: dispositivo.versao_firmware ?? '',
          ip_local: dispositivo.ip_local ?? '',
        }
      : DISPOSITIVO_VAZIO,
  })

  const enviar = handleSubmit(async (valores) => {
    setErroGeral(null)
    const dados = paraDadosDispositivo(valores)
    try {
      if (dispositivo) await atualizar.mutateAsync({ id: dispositivo.id, dados })
      else await criar.mutateAsync(dados)
      mostrar(dispositivo ? 'Dispositivo atualizado.' : 'Dispositivo cadastrado. Os três sensores foram criados.')
      aoFechar()
    } catch (erro) {
      setErroGeral(aplicarErrosDaApi(erro, setError))
    }
  })

  return (
    <Dialogo
      aberto
      aoFechar={aoFechar}
      titulo={dispositivo ? 'Editar dispositivo' : 'Adicionar dispositivo'}
      descricao={
        dispositivo
          ? 'Alterar o MAC faz o sistema passar a aceitar leituras apenas do novo endereço.'
          : 'Informe o endereço MAC do ESP32 instalado neste tanque.'
      }
      rodape={
        <>
          <Botao variante="secundario" onClick={aoFechar} disabled={isSubmitting}>
            Cancelar
          </Botao>
          <Botao type="submit" form="formulario-dispositivo" carregando={isSubmitting}>
            Salvar
          </Botao>
        </>
      }
    >
      <form id="formulario-dispositivo" noValidate onSubmit={enviar} className="space-y-4">
        {erroGeral && (
          <Aviso tom="critico" urgente>
            {erroGeral}
          </Aviso>
        )}
        <CamposDispositivo campo={(nome) => register(nome)} erros={errors} />
      </form>
    </Dialogo>
  )
}

function SeletorStatusSensor({ idTanque, idSensor, status, rotulo }: { idTanque: number; idSensor: number; status: StatusSensor; rotulo: string }) {
  const atualizar = useAtualizarSensor(idTanque)
  const { mostrar } = useToast()
  return (
    <select
      aria-label={`Situação do sensor de ${rotulo}`}
      value={status}
      disabled={atualizar.isPending}
      onChange={(e) =>
        atualizar.mutate(
          { id: idSensor, status: e.target.value as StatusSensor },
          {
            onSuccess: () => mostrar(`Sensor de ${rotulo} atualizado.`),
            onError: (erro) => mostrar(mensagemDeErro(erro), 'erro'),
          },
        )
      }
      className="min-h-9 rounded-lg border border-borda-campo bg-superficie px-2 text-sm pointer-coarse:min-h-11"
    >
      {Object.entries(ROTULO_STATUS_SENSOR).map(([valor, texto]) => (
        <option key={valor} value={valor}>
          {texto}
        </option>
      ))}
    </select>
  )
}

export function GestaoDispositivos({ idTanque }: { idTanque: number }) {
  const dispositivos = useDispositivos(idTanque)
  const [editando, setEditando] = useState<Dispositivo | null | 'novo'>(null)

  return (
    <Cartao aria-labelledby="secao-dispositivos">
      <CabecalhoCartao
        id="secao-dispositivos"
        titulo="Dispositivos e sensores"
        acao={
          <Botao variante="secundario" tamanho="sm" icone={Plus} onClick={() => setEditando('novo')}>
            Adicionar dispositivo
          </Botao>
        }
      />
      {dispositivos.isPending && <Esqueleto className="h-32" />}
      {dispositivos.isError && <EstadoErro erro={dispositivos.error} aoTentarNovamente={() => void dispositivos.refetch()} />}
      {dispositivos.data?.length === 0 && (
        <EstadoVazio
          icone={Cpu}
          titulo="Nenhum dispositivo neste tanque"
          descricao="Cadastre o nó sensor para começar a receber leituras."
          className="py-6"
        />
      )}
      <ul className="space-y-4">
        {dispositivos.data?.map((d) => (
          <li key={d.id} className="rounded-xl border border-borda p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="flex items-center gap-2 font-semibold">
                  <Cpu aria-hidden className="size-4 text-tinta-suave" />
                  {d.nome}
                  <Etiqueta tom={d.status_conexao === 'online' ? 'otimo' : 'atencao'} ponto>
                    {ROTULO_CONEXAO[d.status_conexao]}
                  </Etiqueta>
                </p>
                <p className="mt-1 font-mono text-xs text-tinta-suave">{d.mac_address.toUpperCase()}</p>
                <p className="text-xs text-tinta-suave">
                  {d.modelo_esp32}
                  {d.versao_firmware && ` · firmware ${d.versao_firmware}`}
                  {d.ultima_leitura_em && ` · última leitura ${tempoRelativo(d.ultima_leitura_em)}`}
                </p>
              </div>
              <Botao variante="fantasma" tamanho="sm" icone={Pencil} onClick={() => setEditando(d)}>
                Editar
              </Botao>
            </div>
            <ul className="mt-3 divide-y divide-borda border-t border-borda">
              {d.sensores.map((s) => (
                <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span className="text-sm">
                    {rotuloGrandeza(s.grandeza)} <span className="text-xs text-tinta-suave">({s.modelo})</span>
                  </span>
                  <SeletorStatusSensor idTanque={idTanque} idSensor={s.id} status={s.status} rotulo={rotuloGrandeza(s.grandeza)} />
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      {editando !== null && (
        <DialogoDispositivo
          idTanque={idTanque}
          dispositivo={editando === 'novo' ? null : editando}
          aoFechar={() => setEditando(null)}
        />
      )}
    </Cartao>
  )
}
