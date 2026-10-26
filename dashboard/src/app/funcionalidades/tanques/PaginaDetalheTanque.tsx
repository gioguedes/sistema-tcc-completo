import { Link, useParams } from 'react-router'
import { ArrowLeft, Cpu, Fish, Hourglass, Pencil, Unplug, WifiOff } from 'lucide-react'
import { useAgora, useTituloDocumento } from '@/compartilhado/hooks'
import { formatarHora, formatarNumero, tempoRelativo } from '@/compartilhado/formatacao'
import type { Tanque } from '@/dominio/entidades'
import { ROTULO_CONEXAO, ROTULO_STATUS_SENSOR, ROTULO_STATUS_TANQUE } from '@/dominio/rotulos'
import { situacaoDados } from '@/dominio/situacao'
import { ehErroApi } from '@/infra/api/erros'
import { BotaoLink } from '@/ui/Botao'
import { CabecalhoCartao, Cartao } from '@/ui/Cartao'
import { Aviso, EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { Etiqueta, SeloRisco } from '@/ui/Selos'
import { ControleAerador } from '../../componentes/Aerador'
import { ItemAlerta } from '../../componentes/Alertas'
import { GraficosPorGrandeza } from '../../componentes/Graficos'
import { CartaoVeredito } from '../../componentes/Previsao'
import { ParametrosAtuais } from '../../componentes/Tanque'
import { useAlertas, useLeituras, usePrevisaoAtual } from '../../consultas/monitoramento'
import { useDispositivos, useTanque } from '../../consultas/tanques'
import { usePreferencias, useRotuloGrandeza } from '../../preferencias'
import { useUsuario } from '../autenticacao/ProvedorAutenticacao'

const PERIODO_24H = { tipo: 'relativo', chave: '24h' } as const

function AvisoSituacao({ tanque, agora, admin }: { tanque: Tanque; agora: number; admin: boolean }) {
  const situacao = situacaoDados(tanque)
  if (situacao.tipo === 'offline') {
    return (
      <Aviso tom="atencao" icone={WifiOff} titulo={`Sem dados do sensor ${situacao.ultimaLeitura ? tempoRelativo(situacao.ultimaLeitura, agora) : ''}`.trim()}>
        {situacao.ultimaLeitura && `Última leitura às ${formatarHora(situacao.ultimaLeitura)}. `}
        Os valores abaixo podem estar desatualizados.
      </Aviso>
    )
  }
  if (situacao.tipo === 'sem_dispositivo') {
    return (
      <Aviso
        tom="info"
        icone={Unplug}
        titulo="Nenhum dispositivo cadastrado"
        acao={
          admin && (
            <BotaoLink to={`/tanques/${tanque.id}/editar`} tamanho="sm" variante="secundario">
              Cadastrar
            </BotaoLink>
          )
        }
      >
        Cadastre um dispositivo para começar a monitorar.
      </Aviso>
    )
  }
  if (situacao.tipo === 'aguardando') {
    return (
      <Aviso tom="info" icone={Hourglass} titulo="Aguardando a primeira leitura">
        O nó sensor está cadastrado, mas ainda não enviou dados.
      </Aviso>
    )
  }
  return null
}

function CartaoDispositivos({ idTanque, tanqueNome, agora }: { idTanque: number; tanqueNome: string; agora: number }) {
  const dispositivos = useDispositivos(idTanque)
  const { modoAvancado } = usePreferencias()
  const rotulo = useRotuloGrandeza()
  if (dispositivos.isPending) return <Esqueleto className="h-28" />
  if (dispositivos.isError) return <EstadoErro erro={dispositivos.error} aoTentarNovamente={() => void dispositivos.refetch()} />
  if (dispositivos.data.length === 0) return null
  return (
    <Cartao aria-labelledby="titulo-dispositivos">
      <CabecalhoCartao id="titulo-dispositivos" titulo="Dispositivo" nivel="h2" />
      <ul className="space-y-4">
        {dispositivos.data.map((d) => (
          <li key={d.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="flex items-center gap-2 text-sm font-semibold">
                <Cpu aria-hidden className="size-4 text-tinta-suave" />
                {d.nome}
              </p>
              <Etiqueta tom={d.status_conexao === 'online' ? 'otimo' : 'atencao'} ponto>
                {ROTULO_CONEXAO[d.status_conexao]}
              </Etiqueta>
            </div>
            <p className="mt-1 text-xs text-tinta-suave">
              {d.ultima_leitura_em ? `Última leitura ${tempoRelativo(d.ultima_leitura_em, agora)}` : 'Ainda sem leituras'}
            </p>
            <ControleAerador dispositivo={d} tanqueNome={tanqueNome} agora={agora} />
            {modoAvancado && (
              <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                <dt className="text-tinta-suave">MAC</dt>
                <dd className="font-mono">{d.mac_address}</dd>
                <dt className="text-tinta-suave">Modelo</dt>
                <dd>{d.modelo_esp32}</dd>
                <dt className="text-tinta-suave">Firmware</dt>
                <dd>{d.versao_firmware ?? '—'}</dd>
                {d.sensores.map((s) => (
                  <div key={s.id} className="contents">
                    <dt className="text-tinta-suave">{rotulo(s.grandeza)}</dt>
                    <dd>
                      {s.modelo} · {ROTULO_STATUS_SENSOR[s.status]}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </li>
        ))}
      </ul>
    </Cartao>
  )
}

export default function PaginaDetalheTanque() {
  const { id } = useParams()
  const idTanque = Number(id)
  const usuario = useUsuario()
  const agora = useAgora()
  const tanque = useTanque(idTanque)
  const previsao = usePrevisaoAtual(idTanque)
  const leituras = useLeituras(idTanque, PERIODO_24H)
  const alertas = useAlertas({ tanque: idTanque, porPagina: 3 })
  const naoEncontrado = !Number.isInteger(idTanque) || idTanque <= 0 || ehErroApi(tanque.error, 'nao_encontrado')
  useTituloDocumento(naoEncontrado ? 'Tanque não encontrado' : (tanque.data?.nome ?? 'Tanque'))

  const voltar = (
    <Link to="/tanques" className="inline-flex min-h-9 items-center gap-1 text-sm font-semibold text-primaria pointer-coarse:min-h-11 hover:underline print:hidden">
      <ArrowLeft aria-hidden className="size-4" />
      Tanques
    </Link>
  )

  if (naoEncontrado) {
    return (
      <div className="space-y-4">
        {voltar}
        <Cartao>
          <EstadoVazio
            icone={Fish}
            titulo="Tanque não encontrado"
            descricao="Ele pode ter sido removido ou o endereço está incorreto."
            acao={<BotaoLink to="/tanques" variante="secundario">Ver todos os tanques</BotaoLink>}
          />
        </Cartao>
      </div>
    )
  }
  if (tanque.isPending) {
    return (
      <div className="space-y-6" aria-busy="true">
        <Esqueleto className="h-12 w-64" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <Esqueleto className="h-96" />
          <Esqueleto className="h-96" />
        </div>
      </div>
    )
  }
  if (tanque.isError) return <EstadoErro erro={tanque.error} aoTentarNovamente={() => void tanque.refetch()} />

  const t = tanque.data
  const admin = usuario.perfil === 'admin'
  const situacao = situacaoDados(t)

  return (
    <div className="space-y-6">
      {voltar}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold">
            {t.nome}
            <SeloRisco nivel={t.nivel_risco} />
            {t.status !== 'ativo' && <Etiqueta>{ROTULO_STATUS_TANQUE[t.status]}</Etiqueta>}
          </h1>
          <p className="mt-1 text-sm text-tinta-suave">
            {t.especie ? (
              <>
                {t.especie.nome_comum} (<i>{t.especie.nome_cientifico}</i>)
              </>
            ) : (
              'Espécie não informada'
            )}
            {' · '}
            {formatarNumero(t.volume_litros, 0)} L · {t.quantidade_peixes} {t.quantidade_peixes === 1 ? 'peixe' : 'peixes'}
          </p>
        </div>
        {admin && (
          <BotaoLink to={`/tanques/${t.id}/editar`} variante="secundario" icone={Pencil}>
            Editar
          </BotaoLink>
        )}
      </header>

      <AvisoSituacao tanque={t} agora={agora} admin={admin} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <div className="space-y-6">
          <CartaoVeredito previsao={previsao.data} tanque={t} carregando={previsao.isPending} destaque />
          <Cartao aria-labelledby="titulo-parametros">
            <CabecalhoCartao
              id="titulo-parametros"
              titulo="Parâmetros agora"
              acao={
                situacao.tipo === 'online' && (
                  <span className="text-xs font-semibold text-primaria">Atualizado {tempoRelativo(situacao.ultimaLeitura, agora)}</span>
                )
              }
            />
            <ParametrosAtuais
              leituras={t.ultimas_leituras}
              especie={t.especie}
              ultimaLeitura={t.ultima_leitura_em}
              agora={agora}
            />
            <p className="mt-2 text-xs text-tinta-suave">O oxigênio é estimado a partir da temperatura e do pH.</p>
          </Cartao>
          <CartaoDispositivos idTanque={t.id} tanqueNome={t.nome} agora={agora} />
        </div>

        <div className="min-w-0 space-y-6">
          <section aria-labelledby="titulo-24h">
            <CabecalhoCartao
              id="titulo-24h"
              titulo="Últimas 24 horas"
              link={{ para: `/historico?tanque=${t.id}`, texto: 'Ver histórico completo' }}
            />
            {leituras.isPending && <Esqueleto className="h-80" />}
            {leituras.isError && (
              <Cartao>
                <EstadoErro erro={leituras.error} aoTentarNovamente={() => void leituras.refetch()} />
              </Cartao>
            )}
            {leituras.data && <GraficosPorGrandeza resposta={leituras.data} especie={t.especie} previsao={previsao.data} />}
          </section>

          <Cartao aria-labelledby="titulo-alertas-tanque">
            <CabecalhoCartao
              id="titulo-alertas-tanque"
              titulo="Alertas recentes"
              link={{ para: `/alertas?tanque=${t.id}`, texto: 'Ver todos' }}
            />
            {alertas.isPending && <Esqueleto className="h-24" />}
            {alertas.isError && <EstadoErro erro={alertas.error} aoTentarNovamente={() => void alertas.refetch()} />}
            {alertas.data &&
              (alertas.data.itens.length ? (
                <ul className="-my-3 divide-y divide-borda">
                  {alertas.data.itens.map((a) => (
                    <ItemAlerta key={a.id} alerta={a} agora={agora} />
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-tinta-suave">Nenhum alerta para este tanque.</p>
              ))}
          </Cartao>
        </div>
      </div>
    </div>
  )
}
