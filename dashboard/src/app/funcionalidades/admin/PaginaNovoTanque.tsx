import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router'
import { ArrowLeft, Save } from 'lucide-react'
import { useTituloDocumento } from '@/compartilhado/hooks'
import { esquemaCadastroTanque, esquemaDispositivo, type ValoresCadastroTanque } from '@/dominio/formularios'
import { Botao, BotaoLink } from '@/ui/Botao'
import { CaixaSelecao } from '@/ui/Campos'
import { Cartao } from '@/ui/Cartao'
import { Aviso } from '@/ui/Estados'
import { useToast } from '@/ui/Toast'
import { aplicarErrosDaApi, paraDadosDispositivo } from '../../componentes/formularios'
import { useCriarTanque, useEspecies } from '../../consultas/tanques'
import { CamposDispositivo, DISPOSITIVO_VAZIO } from './CamposDispositivo'
import { CamposTanque } from './CamposTanque'

/** UC01 — Cadastrar tanque e dispositivo (somente administrador). */
export default function PaginaNovoTanque() {
  useTituloDocumento('Novo tanque')
  const navegar = useNavigate()
  const { mostrar } = useToast()
  const especies = useEspecies()
  const criar = useCriarTanque()
  const [erroGeral, setErroGeral] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ValoresCadastroTanque>({
    resolver: zodResolver(esquemaCadastroTanque),
    defaultValues: {
      nome: '',
      quantidade_peixes: 0,
      data_povoamento: '',
      status: 'ativo',
      associar_dispositivo: true,
      dispositivo: DISPOSITIVO_VAZIO,
    },
  })
  const associar = useWatch({ control, name: 'associar_dispositivo' })

  const enviar = handleSubmit(async (valores) => {
    setErroGeral(null)
    try {
      const tanque = await criar.mutateAsync({
        nome: valores.nome,
        id_especie: valores.id_especie,
        volume_litros: valores.volume_litros,
        quantidade_peixes: valores.quantidade_peixes,
        data_povoamento: valores.data_povoamento || null,
        status: valores.status,
        dispositivo: valores.associar_dispositivo
          ? paraDadosDispositivo(esquemaDispositivo.parse(valores.dispositivo))
          : undefined,
      })
      mostrar(`${tanque.nome} cadastrado com sucesso.`)
      navegar(`/tanques/${tanque.id}`)
    } catch (erro) {
      setErroGeral(aplicarErrosDaApi(erro, setError))
    }
  })

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/tanques" className="inline-flex min-h-9 items-center gap-1 text-sm font-semibold text-primaria pointer-coarse:min-h-11 hover:underline">
        <ArrowLeft aria-hidden className="size-4" />
        Tanques
      </Link>
      <header>
        <h1 className="text-2xl font-semibold">Novo tanque</h1>
        <p className="mt-1 text-tinta-suave">Cadastre o tanque e associe o nó sensor (ESP32) pelo endereço MAC.</p>
      </header>

      <form noValidate onSubmit={enviar} className="space-y-6">
        {erroGeral && (
          <Aviso tom="critico" urgente>
            {erroGeral}
          </Aviso>
        )}
        {especies.isError && (
          <Aviso tom="critico" titulo="Não foi possível carregar o catálogo de espécies.">
            Recarregue a página para tentar de novo.
          </Aviso>
        )}

        <Cartao aria-labelledby="secao-tanque">
          <h2 id="secao-tanque" className="mb-4 text-lg font-semibold">
            Dados do tanque
          </h2>
          <CamposTanque
            campo={(nome, opcoes) => register(nome, opcoes)}
            erros={errors}
            especies={especies.data}
            carregandoEspecies={especies.isPending}
          />
        </Cartao>

        <Cartao aria-labelledby="secao-dispositivo">
          <h2 id="secao-dispositivo" className="mb-4 text-lg font-semibold">
            Dispositivo (nó sensor)
          </h2>
          <CaixaSelecao
            rotulo="Associar um dispositivo agora"
            descricao="Os sensores de pH, temperatura e turbidez são criados junto com o dispositivo."
            {...register('associar_dispositivo')}
          />
          {associar && (
            <div className="mt-4">
              <CamposDispositivo campo={(nome) => register(`dispositivo.${nome}`)} erros={errors.dispositivo} />
            </div>
          )}
        </Cartao>

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <BotaoLink to="/tanques" variante="secundario">
            Cancelar
          </BotaoLink>
          <Botao type="submit" icone={Save} carregando={isSubmitting}>
            Cadastrar tanque
          </Botao>
        </div>
      </form>
    </div>
  )
}
