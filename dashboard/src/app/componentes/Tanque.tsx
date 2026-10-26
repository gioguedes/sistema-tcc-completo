import type React from 'react'
import { Link } from 'react-router'
import { ChevronRight, Clock, Droplets, FlaskConical, Hourglass, Thermometer, Unplug, Wind, WifiOff, type LucideIcon } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import { tempoRelativo } from '@/compartilhado/formatacao'
import type { Grandeza, NivelRisco } from '@/dominio/comum'
import type { Especie, LeituraAtual, Tanque } from '@/dominio/entidades'
import { faixaIdealDe, formatarFaixa, formatarValor, GRANDEZAS, ORDEM_GRANDEZAS } from '@/dominio/grandezas'
import { ROTULO_STATUS_TANQUE } from '@/dominio/rotulos'
import { leituraAtrasada, situacaoDados, type SituacaoDados } from '@/dominio/situacao'
import { IlustracaoTanque, InfoPopover, LinhaMetrica } from '@/ui/Pecas'
import { Etiqueta, SeloRisco } from '@/ui/Selos'
import { usePreferencias, useRotuloGrandeza } from '../preferencias'

export const ICONE_GRANDEZA: Record<Grandeza, LucideIcon> = {
  temperatura: Thermometer,
  ph: FlaskConical,
  turbidez: Droplets,
  od: Wind,
}

export function ExplicacaoOd() {
  return (
    <InfoPopover rotulo="Como o oxigênio é estimado">
      O oxigênio dissolvido não é medido por sensor: é estimado a cada 5 minutos por um modelo de Machine
      Learning a partir da temperatura e do pH. Use o valor como indicação, não como medição exata.
    </InfoPopover>
  )
}

interface PropsParametros {
  leituras: LeituraAtual[]
  especie: Especie | null
  /** Leitura mais recente do tanque, para notar a grandeza que ficou para trás (sensor em falha). */
  ultimaLeitura: string | null
  agora: number
}

function Aviso({ children }: { children: string }) {
  return <span className="font-semibold text-atencao">{children}</span>
}

/** Valores mais recentes do tanque, na ordem do Figma. */
export function ParametrosAtuais({ leituras, especie, ultimaLeitura, agora }: PropsParametros) {
  const { modoAvancado } = usePreferencias()
  const rotulo = useRotuloGrandeza()
  return (
    <div>
      {ORDEM_GRANDEZAS.map((g) => {
        const leitura = leituras.find((l) => l.grandeza === g)
        const faixa = faixaIdealDe(g, especie)
        const atrasada = leitura ? leituraAtrasada(leitura, ultimaLeitura) : false
        const avisos: React.ReactNode[] = []
        if (leitura && atrasada) {
          const quando = tempoRelativo(leitura.ts, agora)
          avisos.push(<Aviso key="atraso">{leitura.estimado ? `Estimativa de ${quando}` : `Sensor sem leitura ${quando}`}</Aviso>)
        }
        if (leitura?.baixa_confianca) avisos.push(<Aviso key="confianca">Estimativa de confiança baixa</Aviso>)
        if (modoAvancado && faixa) avisos.push(<span key="faixa">Faixa ideal: {formatarFaixa(g, faixa)}</span>)
        return (
          <LinhaMetrica
            key={g}
            icone={ICONE_GRANDEZA[g]}
            rotulo={
              <span className="inline-flex items-center gap-1">
                {rotulo(g)}
                {GRANDEZAS[g].estimado && <ExplicacaoOd />}
              </span>
            }
            valor={leitura ? formatarValor(g, leitura.valor) : '—'}
            complemento={avisos.length ? <span className="flex flex-col">{avisos}</span> : undefined}
            atenuado={!leitura || atrasada}
          />
        )
      })}
    </div>
  )
}

interface PropsSituacao {
  tanque: Tanque
  agora: number
  /** Textos curtos para listas estreitas (celular). */
  compacto?: boolean
  className?: string
}

export function SituacaoDosDados({ tanque, agora, compacto, className }: PropsSituacao) {
  const situacao = situacaoDados(tanque)
  const estilo: Record<SituacaoDados['tipo'], { icone: LucideIcon; texto: string; classe: string }> = {
    online: {
      icone: Clock,
      texto: situacao.tipo === 'online' ? `Atualizado ${tempoRelativo(situacao.ultimaLeitura, agora)}` : '',
      classe: 'text-tinta-suave',
    },
    offline: {
      icone: WifiOff,
      texto:
        situacao.tipo === 'offline' && situacao.ultimaLeitura
          ? `Sem dados ${compacto ? '' : 'do sensor '}${tempoRelativo(situacao.ultimaLeitura, agora)}`
          : 'Dispositivo offline',
      classe: 'font-semibold text-atencao',
    },
    aguardando: {
      icone: Hourglass,
      texto: compacto ? 'Aguardando leitura' : 'Aguardando a primeira leitura',
      classe: 'text-tinta-suave',
    },
    sem_dispositivo: {
      icone: Unplug,
      texto: compacto ? 'Sem dispositivo' : 'Nenhum dispositivo cadastrado',
      classe: 'text-tinta-suave',
    },
  }
  const { icone: Icone, texto, classe } = estilo[situacao.tipo]
  return (
    <p className={cn('flex items-center gap-1.5 text-xs', classe, className)}>
      <Icone aria-hidden className="size-3.5 shrink-0" />
      {texto}
    </p>
  )
}

/** "Cartão de Tanque" do Figma. O cartão inteiro leva ao detalhe. */
export function CartaoTanque({ tanque, agora }: { tanque: Tanque; agora: number }) {
  return (
    <article className="relative flex flex-col rounded-xl border border-borda bg-superficie p-4 transition-shadow focus-within:ring-2 focus-within:ring-primaria hover:shadow-md">
      {/* o nome quebra linha em vez de virar "Tanque ..."; o selo desce quando não cabe ao lado */}
      <div className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1">
        <h3 className="flex min-w-0 items-center gap-2 font-semibold">
          <span aria-hidden className="size-3.5 shrink-0 rounded-sm bg-primaria" />
          <Link to={`/tanques/${tanque.id}`} className="break-words after:absolute after:inset-0 focus:outline-none">
            {tanque.nome}
          </Link>
        </h3>
        <SeloRisco nivel={tanque.nivel_risco} />
      </div>
      {tanque.status !== 'ativo' && (
        <Etiqueta className="mt-2 self-start">{ROTULO_STATUS_TANQUE[tanque.status]}</Etiqueta>
      )}
      <IlustracaoTanque critico={tanque.nivel_risco === 'critico'} className="mt-3" />
      <div className="mt-2 flex-1">
        <ParametrosAtuais
          leituras={tanque.ultimas_leituras}
          especie={tanque.especie}
          ultimaLeitura={tanque.ultima_leitura_em}
          agora={agora}
        />
      </div>
      <div className="mt-3 flex items-center justify-between gap-2 border-t border-borda pt-3">
        <SituacaoDosDados tanque={tanque} agora={agora} />
        <ChevronRight aria-hidden className="size-4 shrink-0 text-tinta-suave" />
      </div>
    </article>
  )
}

const COR_AVATAR: Record<NivelRisco | 'nulo', string> = {
  critico: 'bg-critico-fundo text-critico',
  atencao: 'bg-atencao-fundo text-atencao',
  otimo: 'bg-otimo-fundo text-otimo',
  nulo: 'bg-neutro-fundo text-tinta-suave',
}

/** Linha compacta da lista "Meus tanques" (celular). */
export function ItemTanque({ tanque, agora }: { tanque: Tanque; agora: number }) {
  return (
    <li>
      <Link
        to={`/tanques/${tanque.id}`}
        className="flex min-h-16 items-center gap-3 rounded-lg px-1 py-2 hover:bg-neutro-fundo"
      >
        <span
          aria-hidden
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold',
            COR_AVATAR[tanque.nivel_risco ?? 'nulo'],
          )}
        >
          {tanque.nome.replace(/^Tanque\s+/i, '').charAt(0).toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold break-words">{tanque.nome}</span>
          <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
            <SeloRisco nivel={tanque.nivel_risco} />
            <SituacaoDosDados tanque={tanque} agora={agora} compacto />
          </span>
        </span>
        <ChevronRight aria-hidden className="size-4 shrink-0 text-tinta-suave" />
      </Link>
    </li>
  )
}
