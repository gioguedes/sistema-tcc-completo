import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate, useParams } from 'react-router'
import { ArrowLeft, Fish, Save } from 'lucide-react'
import { useTituloDocumento } from '@/compartilhado/hooks'
import type { Especie, Tanque } from '@/dominio/entidades'
import { esquemaTanque, type ValoresTanque } from '@/dominio/formularios'
import { ehErroApi } from '@/infra/api/erros'
import { Botao, BotaoLink } from '@/ui/Botao'
import { Cartao } from '@/ui/Cartao'
import { Aviso, EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { useToast } from '@/ui/Toast'
import { aplicarErrosDaApi } from '../../componentes/formularios'
import { useAtualizarTanque, useEspecies, useTanque } from '../../consultas/tanques'
import { CamposTanque } from './CamposTanque'
import { GestaoDispositivos } from './GestaoDispositivos'

function FormularioTanque({ tanque, especies }: { tanque: Tanque; especies: Especie[] }) {
  const navegar = useNavigate()
  const { mostrar } = useToast()
  const atualizar = useAtualizarTanque(tanque.id)
  const [erroGeral, setErroGeral] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ValoresTanque>({
    resolver: zodResolver(esquemaTanque),
    defaultValues: {
      nome: tanque.nome,
      id_especie: tanque.especie?.id,
      volume_litros: tanque.volume_litros,
      quantidade_peixes: tanque.quantidade_peixes,
      data_povoamento: tanque.data_povoamento ?? '',
      status: tanque.status,
    },
  })

  const enviar = handleSubmit(async (valores) => {
    setErroGeral(null)
    try {
      await atualizar.mutateAsync({ ...valores, data_povoamento: valores.data_povoamento || null })
      mostrar('Alterações salvas.')
      navegar(`/tanques/${tanque.id}`)
    } catch (erro) {
      setErroGeral(aplicarErrosDaApi(erro, setError))
    }
  })

  return (
    <form noValidate onSubmit={enviar}>
      <Cartao aria-labelledby="secao-tanque">
        <h2 id="secao-tanque" className="mb-4 text-lg font-semibold">
          Dados do tanque
        </h2>
        {erroGeral && (
          <Aviso tom="critico" urgente className="mb-4">
            {erroGeral}
          </Aviso>
        )}
        <CamposTanque
          campo={(nome, opcoes) => register(nome, opcoes)}
          erros={errors}
          especies={especies}
          carregandoEspecies={false}
        />
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <BotaoLink to={`/tanques/${tanque.id}`} variante="secundario">
            Cancelar
          </BotaoLink>
          <Botao type="submit" icone={Save} carregando={isSubmitting} disabled={!isDirty}>
            Salvar alterações
          </Botao>
        </div>
      </Cartao>
    </form>
  )
}

export default function PaginaEditarTanque() {
  const { id } = useParams()
  const idTanque = Number(id)
  const tanque = useTanque(idTanque)
  // O <select> de espécie só mostra o valor salvo se as opções já existirem ao montar o formulário.
  const especies = useEspecies()
  useTituloDocumento(tanque.data ? `Editar ${tanque.data.nome}` : 'Editar tanque')

  if (!Number.isInteger(idTanque) || ehErroApi(tanque.error, 'nao_encontrado')) {
    return (
      <EstadoVazio
        icone={Fish}
        titulo="Tanque não encontrado"
        acao={<BotaoLink to="/tanques" variante="secundario">Ver todos os tanques</BotaoLink>}
        className="py-16"
      />
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link
        to={`/tanques/${idTanque}`}
        className="inline-flex min-h-9 items-center gap-1 text-sm font-semibold text-primaria pointer-coarse:min-h-11 hover:underline"
      >
        <ArrowLeft aria-hidden className="size-4" />
        {tanque.data?.nome ?? 'Tanque'}
      </Link>
      <header>
        <h1 className="text-2xl font-semibold">Editar tanque</h1>
        <p className="mt-1 text-tinta-suave">Atualize os dados do tanque, seus dispositivos e a situação dos sensores.</p>
      </header>
      {(tanque.isPending || tanque.isPlaceholderData || especies.isPending) && <Esqueleto className="h-96" />}
      {tanque.isError && <EstadoErro erro={tanque.error} aoTentarNovamente={() => void tanque.refetch()} />}
      {especies.isError && <EstadoErro erro={especies.error} aoTentarNovamente={() => void especies.refetch()} />}
      {tanque.data && !tanque.isPlaceholderData && especies.data && (
        <FormularioTanque key={tanque.data.id} tanque={tanque.data} especies={especies.data} />
      )}
      {tanque.data && <GestaoDispositivos idTanque={idTanque} />}
    </div>
  )
}
