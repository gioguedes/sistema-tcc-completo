import { useState } from 'react'
import { AlertOctagon, AlertTriangle, CheckCheck, Clock3, Lightbulb, Power, XCircle } from 'lucide-react'
import { cn } from '@/compartilhado/cn'
import { formatarMomento } from '@/compartilhado/formatacao'
import type { NivelRisco } from '@/dominio/comum'
import type { Alerta, Evento, ResumoDispositivo } from '@/dominio/entidades'
import { ROTULO_CANAL, ROTULO_STATUS_ALERTA } from '@/dominio/rotulos'
import { Botao } from '@/ui/Botao'
import { LinkSeta } from '@/ui/Cartao'
import { DialogoConfirmacao } from '@/ui/Dialogo'
import { ItemEvento } from '@/ui/Pecas'
import { Etiqueta } from '@/ui/Selos'
import { AVISO_OFFLINE, useComandoAerador } from './Aerador'

const COR_PONTO: Record<NivelRisco, string> = {
  otimo: 'bg-otimo',
  atencao: 'bg-atencao',
  critico: 'bg-critico',
}

interface PropsBotaoAerador {
  tanqueNome: string
  dispositivo: ResumoDispositivo | undefined
}

/** Comando manual do aerador no alerta crítico (botão do Figma, F-02), com confirmação explícita. */
export function BotaoAerador({ tanqueNome, dispositivo }: PropsBotaoAerador) {
  const [confirmando, setConfirmando] = useState(false)
  const { enviar, enviando } = useComandoAerador(tanqueNome)
  const offline = dispositivo?.status_conexao !== 'online'

  const confirmar = () => {
    if (dispositivo) enviar(dispositivo.id, 'ligar', () => setConfirmando(false))
  }

  return (
    <>
      <Botao
        variante="perigo"
        larguraTotal
        icone={Power}
        disabled={!dispositivo || offline}
        onClick={() => setConfirmando(true)}
      >
        Ligar aerador
      </Botao>
      {dispositivo && offline && <p className="mt-1 text-center text-xs text-tinta-suave">{AVISO_OFFLINE}</p>}
      <DialogoConfirmacao
        aberto={confirmando}
        titulo="Ligar o aerador?"
        descricao={`O comando será enviado ao ${dispositivo?.nome ?? 'dispositivo'} do ${tanqueNome}.`}
        textoConfirmar="Ligar aerador"
        perigo
        carregando={enviando}
        aoConfirmar={confirmar}
        aoCancelar={() => setConfirmando(false)}
      />
    </>
  )
}

interface PropsCartaoAlerta {
  alerta: Alerta
  dispositivo?: ResumoDispositivo
  agora: number
  titulo?: 'h2' | 'h3'
}

/** "Cartão de Alerta" do Figma, com a recomendação enviada pelo backend. */
export function CartaoAlerta({ alerta, dispositivo, agora, titulo: Titulo = 'h3' }: PropsCartaoAlerta) {
  const critico = alerta.nivel_risco === 'critico'
  const Icone = critico ? AlertOctagon : AlertTriangle
  return (
    <article
      className={cn(
        'rounded-xl border p-4',
        critico ? 'border-critico-borda bg-critico-fundo' : 'border-atencao-borda bg-atencao-fundo',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <Titulo className={cn('flex items-center gap-2 font-semibold', critico ? 'text-critico' : 'text-atencao')}>
          <Icone aria-hidden className="size-5" />
          {critico ? 'Alerta crítico' : 'Atenção'}
        </Titulo>
        <time dateTime={alerta.criado_em} className="text-xs text-tinta-suave tabular-nums">
          {formatarMomento(alerta.criado_em, agora)}
        </time>
      </div>
      <p className="mt-2 font-semibold">{alerta.tanque_nome}</p>
      <p className="text-sm text-tinta-suave">{alerta.mensagem}</p>

      {alerta.recomendacoes.length > 0 && (
        <div className="mt-3 rounded-lg bg-superficie p-3">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <Lightbulb aria-hidden className="size-4 text-atencao" />
            Recomendação
          </p>
          <ul className="mt-1 list-disc space-y-0.5 pl-6 text-sm text-tinta-suave">
            {alerta.recomendacoes.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {critico && alerta.parametro === 'od' && (
        <div className="mt-3">
          <BotaoAerador tanqueNome={alerta.tanque_nome} dispositivo={dispositivo} />
        </div>
      )}

      <LinkSeta para={`/tanques/${alerta.id_tanque}`} className="mt-2">
        Ver detalhes do tanque
      </LinkSeta>
    </article>
  )
}

/** Status de envio pelo WhatsApp, com o tempo até o envio (RNF01: até 60 s). */
export function StatusEnvio({ alerta }: { alerta: Alerta }) {
  if (alerta.status === 'falha') {
    return (
      <Etiqueta tom="critico" icone={XCircle}>
        {ROTULO_STATUS_ALERTA.falha}
      </Etiqueta>
    )
  }
  if (alerta.status === 'pendente' || !alerta.ts_envio) {
    return (
      <Etiqueta tom="neutro" icone={Clock3}>
        {ROTULO_STATUS_ALERTA.pendente}
      </Etiqueta>
    )
  }
  const segundos = Math.round((Date.parse(alerta.ts_envio) - Date.parse(alerta.criado_em)) / 1000)
  return (
    <Etiqueta tom="otimo" icone={CheckCheck}>
      {ROTULO_STATUS_ALERTA.enviado} via {ROTULO_CANAL[alerta.canal]} em {segundos} s
    </Etiqueta>
  )
}

export function ItemAlerta({ alerta, agora }: { alerta: Alerta; agora: number }) {
  return (
    <li className="flex flex-col gap-2 py-3 sm:flex-row sm:items-start">
      <div className="flex min-w-0 flex-1 gap-3">
        <span
          aria-hidden
          className={cn('mt-1.5 size-2.5 shrink-0 rounded-full', alerta.nivel_risco ? COR_PONTO[alerta.nivel_risco] : 'bg-neutro')}
        />
        <div className="min-w-0">
          <p className="text-sm font-semibold">
            {alerta.nivel_risco === 'critico' ? 'Alerta crítico' : 'Atenção'} — {alerta.tanque_nome}
          </p>
          <p className="text-sm text-tinta-suave">{alerta.mensagem}</p>
          <time dateTime={alerta.criado_em} className="text-xs text-tinta-suave">
            {formatarMomento(alerta.criado_em, agora)}
          </time>
        </div>
      </div>
      <div className="pl-5 sm:pl-0">
        <StatusEnvio alerta={alerta} />
      </div>
    </li>
  )
}

export function ItemEventoFeed({ evento, agora }: { evento: Evento; agora: number }) {
  if (evento.tipo === 'alerta') {
    return (
      <ItemEvento
        cor={evento.nivel_risco ? COR_PONTO[evento.nivel_risco] : 'bg-neutro'}
        momento={formatarMomento(evento.ocorrido_em, agora)}
        titulo={`${evento.nivel_risco === 'critico' ? 'Alerta crítico' : 'Atenção'} — ${evento.tanque_nome}`}
        descricao={evento.mensagem}
      />
    )
  }
  return (
    <ItemEvento
      cor="bg-primaria"
      momento={formatarMomento(evento.ocorrido_em, agora)}
      titulo={`Aerador ${evento.acao === 'ligar' ? 'ligado' : 'desligado'} — ${evento.tanque_nome}`}
      descricao={evento.motivo ?? (evento.automatico ? 'Ação automática' : 'Comando manual')}
    />
  )
}
