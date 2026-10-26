import { useSearchParams } from 'react-router'
import { CalendarClock } from 'lucide-react'
import { rotuloDia } from '@/compartilhado/formatacao'
import { useAgora, useTituloDocumento } from '@/compartilhado/hooks'
import type { Evento } from '@/dominio/entidades'
import { Cartao } from '@/ui/Cartao'
import { EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { Paginacao } from '@/ui/Navegacao'
import { ItemEventoFeed } from '../../componentes/Alertas'
import { useEventos } from '../../consultas/monitoramento'

const POR_PAGINA = 15

function agruparPorDia(eventos: Evento[], agora: number) {
  const grupos = new Map<string, Evento[]>()
  for (const evento of eventos) {
    const dia = rotuloDia(evento.ocorrido_em, agora)
    grupos.set(dia, [...(grupos.get(dia) ?? []), evento])
  }
  return [...grupos.entries()]
}

/** Linha do tempo: alertas e acionamentos do aerador, mais recentes primeiro. */
export default function PaginaEventos() {
  useTituloDocumento('Eventos')
  const agora = useAgora()
  const [parametros, setParametros] = useSearchParams()
  const pagina = Math.max(1, Number(parametros.get('pagina')) || 1)
  const eventos = useEventos(pagina, POR_PAGINA)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Eventos</h1>
        <p className="mt-1 text-tinta-suave">Alertas emitidos e acionamentos do aerador em todos os tanques.</p>
      </header>
      <Cartao>
        {eventos.isPending && <Esqueleto className="h-80" />}
        {eventos.isError && <EstadoErro erro={eventos.error} aoTentarNovamente={() => void eventos.refetch()} />}
        {eventos.data?.itens.length === 0 && <EstadoVazio icone={CalendarClock} titulo="Nenhum evento registrado" />}
        {eventos.data && eventos.data.itens.length > 0 && (
          <>
            <div className={`space-y-4 ${eventos.isPlaceholderData ? 'opacity-60' : ''}`}>
              {agruparPorDia(eventos.data.itens, agora).map(([dia, itens]) => (
                <section key={dia} aria-label={dia}>
                  <h2 className="mb-1 text-xs font-semibold tracking-wide text-tinta-suave uppercase">{dia}</h2>
                  <ul className="divide-y divide-borda">
                    {itens.map((e) => (
                      <ItemEventoFeed key={e.id} evento={e} agora={agora} />
                    ))}
                  </ul>
                </section>
              ))}
            </div>
            <Paginacao
              pagina={eventos.data.pagina}
              total={eventos.data.total}
              porPagina={eventos.data.por_pagina}
              aoMudar={(p) => setParametros({ pagina: String(p) })}
            />
          </>
        )}
      </Cartao>
    </div>
  )
}
