import { BrainCircuit, Fish } from 'lucide-react'
import { useTituloDocumento } from '@/compartilhado/hooks'
import { ordenarPorUrgencia } from '@/dominio/situacao'
import { CabecalhoCartao, Cartao, LinkSeta } from '@/ui/Cartao'
import { Aviso, EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { SeloRisco } from '@/ui/Selos'
import { CartaoVeredito, PrevisaoPorHorizonte } from '../../componentes/Previsao'
import { usePrevisoesAtuais } from '../../consultas/monitoramento'
import { useTanques } from '../../consultas/tanques'

/** RF05 — risco previsto pelo serviço de ML para 1, 2 e 3 horas, por tanque. */
export default function PaginaPrevisao() {
  useTituloDocumento('Previsão')
  const tanques = useTanques()
  const lista = ordenarPorUrgencia(tanques.data ?? [])
  const previsoes = usePrevisoesAtuais(lista.map((t) => t.id))

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Previsão</h1>
        <p className="mt-1 text-tinta-suave">Risco previsto para as próximas 1 a 3 horas em cada tanque.</p>
      </header>

      <Aviso tom="info" icone={BrainCircuit}>
        A cada 5 minutos, o serviço de Machine Learning estima o oxigênio dissolvido e prevê o nível de risco a partir
        das leituras de pH e temperatura (a turbidez não entra nos modelos).
      </Aviso>

      {tanques.isPending && <Esqueleto className="h-64" />}
      {tanques.isError && <EstadoErro erro={tanques.error} aoTentarNovamente={() => void tanques.refetch()} />}
      {tanques.data?.length === 0 && (
        <Cartao>
          <EstadoVazio icone={Fish} titulo="Nenhum tanque cadastrado" />
        </Cartao>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {lista.map((tanque, i) => {
          const previsao = previsoes[i]
          return (
            <Cartao key={tanque.id} aria-labelledby={`previsao-${tanque.id}`}>
              <CabecalhoCartao
                id={`previsao-${tanque.id}`}
                titulo={
                  <span className="flex items-center gap-2">
                    {tanque.nome} <SeloRisco nivel={tanque.nivel_risco} />
                  </span>
                }
              />
              {previsao?.isError ? (
                <EstadoErro erro={previsao.error} aoTentarNovamente={() => void previsao.refetch()} />
              ) : (
                <div className="space-y-3">
                  <CartaoVeredito previsao={previsao?.data} tanque={tanque} carregando={previsao?.isPending} />
                  {previsao?.data && previsao.data.horizontes.length > 0 && <PrevisaoPorHorizonte previsao={previsao.data} />}
                </div>
              )}
              <LinkSeta para={`/historico?tanque=${tanque.id}`} className="mt-3">
                Ver no histórico
              </LinkSeta>
            </Cartao>
          )
        })}
      </div>
    </div>
  )
}
