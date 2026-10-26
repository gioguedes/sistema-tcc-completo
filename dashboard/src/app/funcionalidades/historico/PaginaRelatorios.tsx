import { Fish, Printer } from 'lucide-react'
import { formatarDataHora, formatarNumero } from '@/compartilhado/formatacao'
import { useAgora, useTituloDocumento } from '@/compartilhado/hooks'
import { resolverPeriodo, rotuloDoPeriodo } from '@/compartilhado/periodo'
import { faixaIdealDe, formatarFaixa, formatarValor, ORDEM_GRANDEZAS } from '@/dominio/grandezas'
import { ROTULO_STATUS_TANQUE } from '@/dominio/rotulos'
import { Botao } from '@/ui/Botao'
import { Cartao } from '@/ui/Cartao'
import { EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { SeloRisco } from '@/ui/Selos'
import { ItemAlerta } from '../../componentes/Alertas'
import { GraficosPorGrandeza, resumirSerie } from '../../componentes/Graficos'
import { SeletorHistorico, useFiltroHistorico } from '../../componentes/SeletorHistorico'
import { useAlertas, useLeituras } from '../../consultas/monitoramento'
import { useTanques } from '../../consultas/tanques'
import { useRotuloGrandeza } from '../../preferencias'

/** Relatório imprimível do período; "Salvar como PDF" na janela de impressão gera o arquivo. */
export default function PaginaRelatorios() {
  useTituloDocumento('Relatórios')
  const agora = useAgora(60_000)
  const tanques = useTanques()
  const { periodo, tanque, lista, parametros, atualizar } = useFiltroHistorico(tanques.data)
  const leituras = useLeituras(tanque?.id ?? 0, periodo)
  const intervalo = leituras.data
    ? { desde: leituras.data.desde, ate: leituras.data.ate }
    : (() => {
        const { desde, ate } = resolverPeriodo(periodo)
        return { desde: desde.toISOString(), ate: ate.toISOString() }
      })()
  const alertas = useAlertas({ tanque: tanque?.id, porPagina: 50, ...intervalo })
  const rotulo = useRotuloGrandeza()

  if (tanques.isPending) return <Esqueleto className="h-96" />
  if (tanques.isError) return <EstadoErro erro={tanques.error} aoTentarNovamente={() => void tanques.refetch()} />
  if (!tanque) {
    return <EstadoVazio icone={Fish} titulo="Nenhum tanque cadastrado" descricao="Os relatórios aparecem depois que houver tanques." />
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold">Relatórios</h1>
          <p className="mt-1 text-tinta-suave">Escolha o tanque e o período. Para gerar o PDF, use “Salvar como PDF” na impressão.</p>
        </div>
        <Botao icone={Printer} onClick={() => window.print()} disabled={!leituras.data}>
          Imprimir / salvar PDF
        </Botao>
      </header>
      <SeletorHistorico key={parametros.toString()} lista={lista} tanque={tanque} periodo={periodo} atualizar={atualizar} />

      <article className="space-y-6 rounded-xl border border-borda bg-superficie p-4 sm:p-6 print:border-0 print:p-0">
        <header className="border-b border-borda pb-4">
          <p className="text-sm font-semibold text-primaria">Painel Aquícola · Relatório de qualidade da água</p>
          <h2 className="mt-1 flex flex-wrap items-center gap-2 text-xl font-semibold">
            {tanque.nome} <SeloRisco nivel={tanque.nivel_risco} />
          </h2>
          <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            <div className="flex gap-2">
              <dt className="text-tinta-suave">Período:</dt>
              <dd>
                {rotuloDoPeriodo(periodo)} ({formatarDataHora(intervalo.desde)} a {formatarDataHora(intervalo.ate)})
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-tinta-suave">Gerado em:</dt>
              <dd>{formatarDataHora(agora)}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-tinta-suave">Espécie:</dt>
              <dd>{tanque.especie ? `${tanque.especie.nome_comum} (${tanque.especie.nome_cientifico})` : 'Não informada'}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-tinta-suave">Tanque:</dt>
              <dd>
                {formatarNumero(tanque.volume_litros, 0)} L · {tanque.quantidade_peixes} peixes · {ROTULO_STATUS_TANQUE[tanque.status]}
              </dd>
            </div>
          </dl>
        </header>

        {leituras.isPending && <Esqueleto className="h-64" />}
        {leituras.isError && <EstadoErro erro={leituras.error} aoTentarNovamente={() => void leituras.refetch()} />}
        {leituras.data && (
          <>
            <section aria-labelledby="titulo-resumo">
              <h3 id="titulo-resumo" className="mb-3 font-semibold">
                Resumo do período
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[34rem] text-left text-sm">
                  <thead className="border-b border-borda text-xs text-tinta-suave">
                    <tr>
                      <th scope="col" className="py-2 font-semibold">Grandeza</th>
                      <th scope="col" className="py-2 text-right font-semibold">Mínimo</th>
                      <th scope="col" className="py-2 text-right font-semibold">Média</th>
                      <th scope="col" className="py-2 text-right font-semibold">Máximo</th>
                      <th scope="col" className="py-2 text-right font-semibold">Faixa ideal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-borda tabular-nums">
                    {ORDEM_GRANDEZAS.map((g) => {
                      const resumo = resumirSerie(leituras.data.series.find((s) => s.grandeza === g))
                      const faixa = faixaIdealDe(g, tanque.especie)
                      return (
                        <tr key={g}>
                          <th scope="row" className="py-2 font-semibold">{rotulo(g)}</th>
                          <td className="py-2 text-right">{resumo ? formatarValor(g, resumo.minimo) : '—'}</td>
                          <td className="py-2 text-right">{resumo ? formatarValor(g, resumo.media) : '—'}</td>
                          <td className="py-2 text-right">{resumo ? formatarValor(g, resumo.maximo) : '—'}</td>
                          <td className="py-2 text-right text-tinta-suave">{faixa ? formatarFaixa(g, faixa) : 'Não definida'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>
            <GraficosPorGrandeza resposta={leituras.data} especie={tanque.especie} altura={150} className="print:grid-cols-2" />
          </>
        )}

        <Cartao aria-labelledby="titulo-alertas-periodo" className="break-inside-avoid">
          <h3 id="titulo-alertas-periodo" className="mb-2 font-semibold">
            Alertas no período
          </h3>
          {alertas.isPending && <Esqueleto className="h-20" />}
          {alertas.isError && <EstadoErro erro={alertas.error} aoTentarNovamente={() => void alertas.refetch()} />}
          {alertas.data &&
            (alertas.data.itens.length ? (
              <ul className="divide-y divide-borda">
                {alertas.data.itens.map((a) => (
                  <ItemAlerta key={a.id} alerta={a} agora={agora} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-tinta-suave">Nenhum alerta no período.</p>
            ))}
        </Cartao>
      </article>
    </div>
  )
}
