import { useState } from 'react'
import { Link } from 'react-router'
import { AlertOctagon, AlertTriangle, CheckCircle2, Fish, Plus } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import { useAgora, useTituloDocumento } from '@/compartilhado/hooks'
import { pluralizar, primeiroNome, saudacao } from '@/compartilhado/formatacao'
import { OPCOES_PERIODO, type ChavePeriodo } from '@/compartilhado/periodo'
import { ordenarPorUrgencia } from '@/dominio/situacao'
import { BotaoLink } from '@/ui/Botao'
import { CabecalhoCartao, Cartao, LinkSeta } from '@/ui/Cartao'
import { Aviso, EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { SeletorSegmentado } from '@/ui/Navegacao'
import { CartaoIndicador } from '@/ui/Pecas'
import { SeloRisco } from '@/ui/Selos'
import { CartaoAlerta, ItemEventoFeed } from '../../componentes/Alertas'
import { ConviteInstalacao } from '../../componentes/Aplicativo'
import { GraficoQualidade } from '../../componentes/Graficos'
import { CartaoTanque, ItemTanque } from '../../componentes/Tanque'
import { useAlertasAtivos, useEventos } from '../../consultas/monitoramento'
import { useTanques } from '../../consultas/tanques'
import { useUsuario } from '../autenticacao/ProvedorAutenticacao'

function EsqueletoInicio() {
  return (
    <div className="space-y-6" aria-busy="true">
      <Esqueleto className="h-14 w-72" />
      <div className="grid grid-cols-3 gap-3">
        <Esqueleto className="h-24" />
        <Esqueleto className="h-24" />
        <Esqueleto className="h-24" />
      </div>
      <Esqueleto className="h-72" />
    </div>
  )
}

function CartaoUltimosEventos({ agora }: { agora: number }) {
  const eventos = useEventos(1, 4)
  return (
    <Cartao aria-labelledby="titulo-eventos">
      <CabecalhoCartao id="titulo-eventos" titulo="Últimos eventos" link={{ para: '/eventos', texto: 'Ver todos' }} />
      {eventos.isPending && <Esqueleto className="h-40" />}
      {eventos.isError && <EstadoErro erro={eventos.error} aoTentarNovamente={() => void eventos.refetch()} />}
      {eventos.data &&
        (eventos.data.itens.length ? (
          <ul className="-my-2">
            {eventos.data.itens.map((e) => (
              <ItemEventoFeed key={e.id} evento={e} agora={agora} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-tinta-suave">Nenhum evento registrado ainda.</p>
        ))}
    </Cartao>
  )
}

export default function PaginaInicio() {
  useTituloDocumento('Início')
  const usuario = useUsuario()
  const agora = useAgora()
  const tanques = useTanques()
  const alertasAtivos = useAlertasAtivos()
  const [periodo, setPeriodo] = useState<ChavePeriodo>('24h')
  const [idDestaque, setIdDestaque] = useState<number | null>(null)

  if (tanques.isPending) return <EsqueletoInicio />
  if (tanques.isError) return <EstadoErro erro={tanques.error} aoTentarNovamente={() => void tanques.refetch()} />

  const lista = ordenarPorUrgencia(tanques.data)
  const cabecalho = (
    <header>
      <h1 className="text-2xl font-semibold">
        {saudacao()}, {primeiroNome(usuario.nome)}.
      </h1>
      <p className="mt-1 text-tinta-suave">Aqui está o resumo da situação dos seus tanques.</p>
    </header>
  )

  if (lista.length === 0) {
    return (
      <div className="space-y-6">
        {cabecalho}
        <Cartao>
          <EstadoVazio
            icone={Fish}
            titulo="Nenhum tanque cadastrado"
            descricao={
              usuario.perfil === 'admin'
                ? 'Cadastre um tanque e associe o nó sensor para começar a monitorar.'
                : 'Peça ao administrador para cadastrar os tanques que você acompanha.'
            }
            acao={
              usuario.perfil === 'admin' && (
                <BotaoLink to="/tanques/novo" icone={Plus}>
                  Cadastrar tanque
                </BotaoLink>
              )
            }
          />
        </Cartao>
      </div>
    )
  }

  const contagem = { otimo: 0, atencao: 0, critico: 0 }
  for (const t of lista) if (t.nivel_risco) contagem[t.nivel_risco]++
  const destaque = lista.find((t) => t.id === idDestaque) ?? lista[0]!
  const alertas = alertasAtivos.data?.itens ?? []
  const alertaPrincipal = alertas.find((a) => a.nivel_risco === 'critico') ?? alertas[0]
  const dispositivoDoAlerta = alertaPrincipal
    ? lista.find((t) => t.id === alertaPrincipal.id_tanque)?.dispositivos[0]
    : undefined
  const deTotal = `de ${lista.length} ${pluralizar(lista.length, 'tanque', 'tanques')}`

  return (
    <div className="space-y-6">
      {cabecalho}
      <ConviteInstalacao />

      <section aria-label="Resumo por situação" className="grid grid-cols-3 gap-2 sm:gap-4">
        <CartaoIndicador tom="otimo" icone={CheckCircle2} rotulo="Ótimo" valor={contagem.otimo} detalhe={deTotal} />
        <CartaoIndicador tom="atencao" icone={AlertTriangle} rotulo="Atenção" valor={contagem.atencao} detalhe={deTotal} />
        <CartaoIndicador tom="critico" icone={AlertOctagon} rotulo="Crítico" valor={contagem.critico} detalhe={deTotal} />
      </section>

      {contagem.critico > 0 && (
        <Aviso tom="critico" titulo={`${contagem.critico} ${pluralizar(contagem.critico, 'tanque precisa', 'tanques precisam')} de ação agora`} acao={<LinkSeta para="/alertas">Ver</LinkSeta>} />
      )}

      {/* No xl, mesma grade de 3 colunas do resumo: alertas e eventos ficam embaixo do cartão "Crítico" */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3 xl:gap-x-4">
        <section aria-labelledby="titulo-tanques" className="flex min-w-0 flex-col xl:col-span-2">
          <CabecalhoCartao
            id="titulo-tanques"
            titulo={<span>Seus tanques</span>}
            link={{ para: '/tanques', texto: 'Ver todos os tanques' }}
          />
          <ul className="divide-y divide-borda rounded-xl border border-borda bg-superficie px-3 sm:hidden">
            {lista.slice(0, 5).map((t) => (
              <ItemTanque key={t.id} tanque={t} agora={agora} />
            ))}
          </ul>
          {/* 3 colunas só a partir de 1536 px: com a barra lateral, em 1024 px cada cartão ficava com ~220 px e cortava o nome */}
          {/* flex-1: no xl, os cartões esticam até o fim da coluna de alertas e eventos */}
          <div className="hidden flex-1 gap-4 sm:grid sm:grid-cols-2 2xl:grid-cols-3">
            {lista.slice(0, 4).map((t, i) => (
              // O 4º cartão só aparece nas grades de 2 colunas, para fechar 2 × 2.
              <div key={t.id} className={i === 3 ? 'grid 2xl:hidden' : 'grid'}>
                <CartaoTanque tanque={t} agora={agora} />
              </div>
            ))}
            {usuario.perfil === 'admin' && (
              // Ocupa a vaga que sobra na última fileira (2 colunas até o 2xl, 3 a partir dele)
              <Link
                to="/tanques/novo"
                className={cn(
                  'flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-borda p-4 text-center text-tinta-suave transition-colors hover:border-primaria hover:text-primaria',
                  lista.length < 4 && lista.length % 2 === 1 ? 'flex' : 'hidden',
                  lista.length < 3 ? '2xl:flex' : '2xl:hidden',
                  lista.length === 1 && '2xl:col-span-2',
                )}
              >
                <Plus aria-hidden className="size-6" />
                <span className="font-semibold">Cadastrar tanque</span>
                <span className="text-xs">Associe um nó sensor para monitorar outro tanque.</span>
              </Link>
            )}
          </div>
        </section>

        {/* No xl, o gráfico ocupa a largura toda, abaixo dos tanques e da coluna de alertas e eventos */}
        <Cartao aria-labelledby="titulo-grafico" className="min-w-0 xl:col-span-3 xl:row-start-2">
          <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <h2 id="titulo-grafico" className="flex flex-wrap items-center gap-2 text-base font-semibold sm:text-lg">
              Qualidade da água — {destaque.nome}
              <SeloRisco nivel={destaque.nivel_risco} />
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              <label className="sr-only" htmlFor="tanque-grafico">
                Tanque exibido no gráfico
              </label>
              <select
                id="tanque-grafico"
                value={destaque.id}
                onChange={(e) => setIdDestaque(Number(e.target.value))}
                className="min-h-9 rounded-lg border border-borda-campo bg-superficie px-2 text-sm pointer-coarse:min-h-11"
              >
                {lista.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nome}
                  </option>
                ))}
              </select>
              <SeletorSegmentado rotulo="Período do gráfico" opcoes={OPCOES_PERIODO} valor={periodo} aoMudar={setPeriodo} />
            </div>
          </div>
          <GraficoQualidade tanque={destaque} periodo={{ tipo: 'relativo', chave: periodo }} />
        </Cartao>

        <aside className="space-y-6 xl:col-start-3 xl:row-start-1" aria-label="Alertas e eventos">
          {alertasAtivos.isPending ? (
            <Esqueleto className="h-64" />
          ) : alertaPrincipal ? (
            <CartaoAlerta alerta={alertaPrincipal} dispositivo={dispositivoDoAlerta} agora={agora} titulo="h2" />
          ) : (
            <Aviso tom="otimo" titulo="Nenhum alerta ativo">
              Nenhum tanque pede ação no momento.
            </Aviso>
          )}
          <CartaoUltimosEventos agora={agora} />
        </aside>
      </div>
    </div>
  )
}
