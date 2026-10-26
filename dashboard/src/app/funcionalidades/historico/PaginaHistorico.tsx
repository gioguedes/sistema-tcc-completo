import { Download, FileText, Fish } from 'lucide-react'
import { baixarCsv, nomeDeArquivo } from '@/compartilhado/csv'
import { formatarDataHora } from '@/compartilhado/formatacao'
import { useTituloDocumento } from '@/compartilhado/hooks'
import { rotuloDoPeriodo } from '@/compartilhado/periodo'
import type { RespostaLeituras, Tanque } from '@/dominio/entidades'
import { GRANDEZAS } from '@/dominio/grandezas'
import { motivoSemPrevisao } from '@/dominio/situacao'
import { Botao, BotaoLink } from '@/ui/Botao'
import { Cartao } from '@/ui/Cartao'
import { EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { SeloRisco } from '@/ui/Selos'
import { GraficosPorGrandeza } from '../../componentes/Graficos'
import { PrevisaoPorHorizonte } from '../../componentes/Previsao'
import { SeletorHistorico, useFiltroHistorico } from '../../componentes/SeletorHistorico'
import { useLeituras, usePrevisaoAtual } from '../../consultas/monitoramento'
import { useTanques } from '../../consultas/tanques'
import { useRotuloGrandeza } from '../../preferencias'

function exportarCsv(tanque: Tanque, resposta: RespostaLeituras, rotulo: (g: keyof typeof GRANDEZAS) => string) {
  const linhas = resposta.series.flatMap((serie) =>
    serie.pontos.map((p) => [
      formatarDataHora(p.ts),
      rotulo(serie.grandeza),
      p.valor,
      GRANDEZAS[serie.grandeza].unidade || 'pH',
      p.min ?? '',
      p.max ?? '',
    ]),
  )
  baixarCsv(
    `historico-${nomeDeArquivo(tanque.nome)}-${resposta.desde.slice(0, 10)}-a-${resposta.ate.slice(0, 10)}.csv`,
    ['Data e hora', 'Grandeza', 'Valor', 'Unidade', 'Mínimo no intervalo', 'Máximo no intervalo'],
    linhas,
  )
}

export default function PaginaHistorico() {
  useTituloDocumento('Histórico')
  const tanques = useTanques()
  const { periodo, tanque, lista, parametros, atualizar } = useFiltroHistorico(tanques.data)
  const leituras = useLeituras(tanque?.id ?? 0, periodo)
  const previsao = usePrevisaoAtual(tanque?.id ?? 0)
  const rotulo = useRotuloGrandeza()

  const cabecalho = (
    <header>
      <h1 className="text-2xl font-semibold">Histórico</h1>
      <p className="mt-1 text-tinta-suave">Leituras de pH, temperatura, turbidez e oxigênio estimado ao longo do tempo.</p>
    </header>
  )

  if (tanques.isPending) return <div className="space-y-6">{cabecalho}<Esqueleto className="h-96" /></div>
  if (tanques.isError) return <EstadoErro erro={tanques.error} aoTentarNovamente={() => void tanques.refetch()} />
  if (!tanque) {
    return (
      <div className="space-y-6">
        {cabecalho}
        <Cartao>
          <EstadoVazio icone={Fish} titulo="Nenhum tanque cadastrado" descricao="O histórico aparece depois que houver tanques." />
        </Cartao>
      </div>
    )
  }

  const mostrarPrevisao = periodo.tipo === 'relativo'

  return (
    <div className="space-y-6">
      {cabecalho}
      <SeletorHistorico key={parametros.toString()} lista={lista} tanque={tanque} periodo={periodo} atualizar={atualizar} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex flex-wrap items-center gap-2 text-lg font-semibold">
          {tanque.nome}
          <SeloRisco nivel={tanque.nivel_risco} />
          <span className="text-sm font-normal text-tinta-suave">· {rotuloDoPeriodo(periodo)}</span>
        </h2>
        <div className="flex flex-wrap gap-2">
          <Botao
            variante="secundario"
            tamanho="sm"
            icone={Download}
            disabled={!leituras.data}
            onClick={() => leituras.data && exportarCsv(tanque, leituras.data, rotulo)}
          >
            Exportar CSV
          </Botao>
          <BotaoLink to={`/relatorios?${parametros.toString() || `tanque=${tanque.id}`}`} variante="secundario" tamanho="sm" icone={FileText}>
            Exportar relatório (PDF)
          </BotaoLink>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0">
          {leituras.isPending && <Esqueleto className="h-96" />}
          {leituras.isError && (
            <Cartao>
              <EstadoErro erro={leituras.error} aoTentarNovamente={() => void leituras.refetch()} />
            </Cartao>
          )}
          {leituras.data && (
            <div className={leituras.isPlaceholderData ? 'opacity-60 transition-opacity' : undefined} aria-busy={leituras.isPlaceholderData}>
              <GraficosPorGrandeza
                resposta={leituras.data}
                especie={tanque.especie}
                previsao={mostrarPrevisao ? previsao.data : undefined}
                mostrarResumo
              />
            </div>
          )}
        </div>
        <aside>
          <Cartao aria-labelledby="titulo-previsao" className="border-primaria/20 bg-primaria-fundo">
            <h2 id="titulo-previsao" className="mb-2 font-semibold text-primaria-escura">
              Previsão de risco
            </h2>
            {previsao.isPending ? (
              <Esqueleto className="h-32" />
            ) : previsao.data?.od_atual || previsao.data?.horizontes.length ? (
              <PrevisaoPorHorizonte previsao={previsao.data} />
            ) : (
              <p className="text-sm text-tinta-suave">Previsão indisponível. {motivoSemPrevisao(tanque)}</p>
            )}
          </Cartao>
        </aside>
      </div>
    </div>
  )
}
