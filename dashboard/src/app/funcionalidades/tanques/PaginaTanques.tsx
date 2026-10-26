import { useSearchParams } from 'react-router'
import { Fish, Plus, SearchX } from 'lucide-react'
import { useAgora, useTituloDocumento } from '@/compartilhado/hooks'
import type { NivelRisco } from '@/dominio/comum'
import { ordenarPorUrgencia } from '@/dominio/situacao'
import { BotaoLink } from '@/ui/Botao'
import { CampoBusca } from '@/ui/Campos'
import { Cartao } from '@/ui/Cartao'
import { EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { SeletorSegmentado } from '@/ui/Navegacao'
import { CartaoTanque } from '../../componentes/Tanque'
import { useTanques } from '../../consultas/tanques'
import { useUsuario } from '../autenticacao/ProvedorAutenticacao'

type Filtro = 'todos' | NivelRisco

const FILTROS: { valor: Filtro; rotulo: string }[] = [
  { valor: 'todos', rotulo: 'Todos' },
  { valor: 'critico', rotulo: 'Crítico' },
  { valor: 'atencao', rotulo: 'Atenção' },
  { valor: 'otimo', rotulo: 'Ótimo' },
]

const normalizar = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

export default function PaginaTanques() {
  useTituloDocumento('Tanques')
  const usuario = useUsuario()
  const agora = useAgora()
  const tanques = useTanques()
  const [parametros, setParametros] = useSearchParams()
  const busca = parametros.get('busca') ?? ''
  const filtro = (FILTROS.find((f) => f.valor === parametros.get('situacao'))?.valor ?? 'todos') as Filtro

  const atualizar = (chave: string, valor: string) =>
    setParametros(
      (atuais) => {
        if (valor && valor !== 'todos') atuais.set(chave, valor)
        else atuais.delete(chave)
        return atuais
      },
      { replace: true },
    )

  const lista = ordenarPorUrgencia(tanques.data ?? []).filter(
    (t) =>
      (filtro === 'todos' || t.nivel_risco === filtro) &&
      (!busca || normalizar(`${t.nome} ${t.especie?.nome_comum ?? ''}`).includes(normalizar(busca))),
  )

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Tanques</h1>
          <p className="mt-1 text-tinta-suave">
            {tanques.data ? `${tanques.data.length} tanques monitorados` : 'Todos os tanques monitorados'}
          </p>
        </div>
        {usuario.perfil === 'admin' && (
          <BotaoLink to="/tanques/novo" icone={Plus}>
            Novo tanque
          </BotaoLink>
        )}
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <CampoBusca
          rotulo="Buscar tanque"
          placeholder="Buscar tanque…"
          value={busca}
          onChange={(e) => atualizar('busca', e.target.value)}
          className="sm:max-w-xs sm:flex-1"
        />
        <SeletorSegmentado
          rotulo="Filtrar por situação"
          opcoes={FILTROS}
          valor={filtro}
          aoMudar={(v) => atualizar('situacao', v)}
          className="self-start"
        />
      </div>

      {tanques.isPending && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((n) => (
            <Esqueleto key={n} className="h-80" />
          ))}
        </div>
      )}
      {tanques.isError && (
        <Cartao>
          <EstadoErro erro={tanques.error} aoTentarNovamente={() => void tanques.refetch()} />
        </Cartao>
      )}
      {tanques.data && tanques.data.length === 0 && (
        <Cartao>
          <EstadoVazio
            icone={Fish}
            titulo="Nenhum tanque cadastrado"
            descricao={
              usuario.perfil === 'admin'
                ? 'Cadastre o primeiro tanque para começar.'
                : 'Peça ao administrador para cadastrar os tanques.'
            }
          />
        </Cartao>
      )}
      {tanques.data && tanques.data.length > 0 && lista.length === 0 && (
        <Cartao>
          <EstadoVazio icone={SearchX} titulo="Nenhum tanque encontrado" descricao="Tente outro nome ou outro filtro." />
        </Cartao>
      )}
      {lista.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {lista.map((t) => (
            <CartaoTanque key={t.id} tanque={t} agora={agora} />
          ))}
        </div>
      )}
    </div>
  )
}
