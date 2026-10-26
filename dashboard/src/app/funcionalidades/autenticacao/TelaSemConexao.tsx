import { useEffect, useState } from 'react'
import { Clock, RotateCw, WifiOff } from 'lucide-react'
import { formatarDataHora, formatarMomento, tempoRelativo } from '@/compartilhado/formatacao'
import { useAgora, useOnline, useTituloDocumento } from '@/compartilhado/hooks'
import type { Tanque } from '@/dominio/entidades'
import { lerUltimaLeitura, type CopiaLocal } from '@/infra/armazenamento/ultimaLeitura'
import { Botao } from '@/ui/Botao'
import { Aviso, Carregando } from '@/ui/Estados'
import { SeloRisco } from '@/ui/Selos'
import { ParametrosAtuais } from '../../componentes/Tanque'
import { Marca } from '../../layouts/LayoutApp'
import { useAutenticacao } from './ProvedorAutenticacao'

/** Cartão só de leitura: sem rede não há detalhe para abrir. */
function CartaoUltimaLeitura({ tanque, agora }: { tanque: Tanque; agora: number }) {
  return (
    <article className="flex flex-col rounded-xl border border-borda bg-superficie p-4">
      <h2 className="font-semibold break-words">{tanque.nome}</h2>
      <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-tinta-suave">
        <SeloRisco nivel={tanque.nivel_risco} />
        na última leitura
      </p>
      <div className="mt-2 flex-1">
        <ParametrosAtuais
          leituras={tanque.ultimas_leituras}
          especie={tanque.especie}
          ultimaLeitura={tanque.ultima_leitura_em}
          agora={agora}
        />
      </div>
      <p className="mt-3 flex items-center gap-1.5 border-t border-borda pt-3 text-xs font-semibold text-atencao">
        <Clock aria-hidden className="size-3.5 shrink-0" />
        {tanque.ultima_leitura_em
          ? `Medido ${tempoRelativo(tanque.ultima_leitura_em, agora)} (${formatarMomento(tanque.ultima_leitura_em, agora)})`
          : 'Sem leitura registrada'}
      </p>
    </article>
  )
}

/**
 * Abertura sem rede (TC2 §9): mostra a última leitura salva neste aparelho, sempre com o horário
 * e o aviso de que pode estar desatualizada. Mostrar um número antigo como atual, num sistema de alerta,
 * seria uma falha de segurança de uso.
 */
export function TelaSemConexao() {
  useTituloDocumento('Sem conexão')
  const { tentarNovamente } = useAutenticacao()
  const online = useOnline()
  const agora = useAgora()
  const [copia, setCopia] = useState<CopiaLocal | null | undefined>(undefined)

  useEffect(() => {
    let ativo = true
    void lerUltimaLeitura().then((lida) => {
      if (ativo) setCopia(lida)
    })
    return () => {
      ativo = false
    }
  }, [])

  const tanques = copia?.tanques ?? []

  return (
    <div className="min-h-dvh">
      <header className="border-b border-borda bg-superficie">
        <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
          <Marca />
        </div>
      </header>

      <main id="conteudo" className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold">{tanques.length ? 'Última leitura salva' : 'Sem conexão'}</h1>

        <div className="space-y-3">
          <Aviso
            tom="atencao"
            icone={WifiOff}
            urgente
            titulo={online ? 'Não foi possível falar com o servidor.' : 'Você está sem internet.'}
          >
            {copia &&
              tanques.length > 0 &&
              `Estes dados foram salvos neste aparelho em ${formatarDataHora(copia.salvoEm)} e podem não mostrar a situação atual dos tanques. `}
            {copia !== undefined && !tanques.length && 'Ainda não há leitura salva neste aparelho. '}
            O painel volta a atualizar sozinho quando a conexão voltar.
          </Aviso>
          <Botao variante="secundario" tamanho="sm" icone={RotateCw} onClick={tentarNovamente}>
            Tentar novamente
          </Botao>
        </div>

        {copia === undefined && <Carregando texto="Procurando a última leitura salva…" />}

        {tanques.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
            {tanques.map((t) => (
              <CartaoUltimaLeitura key={t.id} tanque={t} agora={agora} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
