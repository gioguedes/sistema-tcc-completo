import { useSearchParams } from 'react-router'
import { BellOff } from 'lucide-react'
import { useAgora, useTituloDocumento } from '@/compartilhado/hooks'
import type { StatusAlerta } from '@/dominio/comum'
import { ROTULO_STATUS_ALERTA } from '@/dominio/rotulos'
import { CabecalhoCartao, Cartao } from '@/ui/Cartao'
import { Selecao } from '@/ui/Campos'
import { Aviso, EstadoErro, EstadoVazio, Esqueleto } from '@/ui/Estados'
import { Paginacao } from '@/ui/Navegacao'
import { CartaoAlerta, ItemAlerta } from '../../componentes/Alertas'
import { useAlertas, useAlertasAtivos } from '../../consultas/monitoramento'
import { useTanques } from '../../consultas/tanques'

const POR_PAGINA = 10

export default function PaginaAlertas() {
  useTituloDocumento('Alertas')
  const agora = useAgora()
  const tanques = useTanques()
  const ativos = useAlertasAtivos()
  const [parametros, setParametros] = useSearchParams()
  const tanque = Number(parametros.get('tanque')) || undefined
  const status = (Object.keys(ROTULO_STATUS_ALERTA) as StatusAlerta[]).find((s) => s === parametros.get('status'))
  const pagina = Math.max(1, Number(parametros.get('pagina')) || 1)
  const historico = useAlertas({ tanque, status, pagina, porPagina: POR_PAGINA })

  const filtrar = (chave: string, valor: string) =>
    setParametros((atuais) => {
      if (valor) atuais.set(chave, valor)
      else atuais.delete(chave)
      if (chave !== 'pagina') atuais.delete('pagina')
      return atuais
    })

  const ativosFiltrados = (ativos.data?.itens ?? []).filter((a) => !tanque || a.id_tanque === tanque)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Alertas e recomendações</h1>
        <p className="mt-1 text-tinta-suave">O que precisa de ação agora e o histórico de alertas enviados.</p>
      </header>

      <section aria-labelledby="titulo-ativos" className="space-y-4">
        <h2 id="titulo-ativos" className="text-lg font-semibold">
          Precisam de atenção agora
        </h2>
        {ativos.isPending && <Esqueleto className="h-48" />}
        {ativos.isError && (
          <Cartao>
            <EstadoErro erro={ativos.error} aoTentarNovamente={() => void ativos.refetch()} />
          </Cartao>
        )}
        {ativos.data && ativosFiltrados.length === 0 && (
          <Aviso tom="otimo" titulo="Nenhum tanque pede ação agora.">
            Os alertas aparecem aqui assim que a previsão indicar atenção ou risco crítico.
          </Aviso>
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {ativosFiltrados.map((alerta) => (
            <CartaoAlerta
              key={alerta.id}
              alerta={alerta}
              agora={agora}
              dispositivo={tanques.data?.find((t) => t.id === alerta.id_tanque)?.dispositivos[0]}
            />
          ))}
        </div>
      </section>

      <Cartao aria-labelledby="titulo-historico-alertas">
        <CabecalhoCartao id="titulo-historico-alertas" titulo="Histórico de alertas" />
        <div className="mb-2 grid gap-3 sm:grid-cols-2 lg:max-w-xl">
          <Selecao rotulo="Tanque" value={tanque ?? ''} onChange={(e) => filtrar('tanque', e.target.value)}>
            <option value="">Todos os tanques</option>
            {tanques.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </Selecao>
          <Selecao rotulo="Envio pelo WhatsApp" value={status ?? ''} onChange={(e) => filtrar('status', e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(ROTULO_STATUS_ALERTA).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </Selecao>
        </div>
        {historico.isPending && <Esqueleto className="h-64" />}
        {historico.isError && <EstadoErro erro={historico.error} aoTentarNovamente={() => void historico.refetch()} />}
        {historico.data &&
          (historico.data.itens.length === 0 ? (
            <EstadoVazio icone={BellOff} titulo="Nenhum alerta encontrado" descricao="Tente outros filtros." className="py-8" />
          ) : (
            <>
              <ul className={`divide-y divide-borda ${historico.isPlaceholderData ? 'opacity-60' : ''}`}>
                {historico.data.itens.map((a) => (
                  <ItemAlerta key={a.id} alerta={a} agora={agora} />
                ))}
              </ul>
              <Paginacao
                pagina={historico.data.pagina}
                total={historico.data.total}
                porPagina={historico.data.por_pagina}
                aoMudar={(p) => filtrar('pagina', String(p))}
              />
            </>
          ))}
      </Cartao>
    </div>
  )
}
