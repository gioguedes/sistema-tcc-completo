import { Download, Smartphone } from 'lucide-react'
import { Botao } from '@/ui/Botao'
import { CabecalhoCartao, Cartao } from '@/ui/Cartao'
import { Aviso } from '@/ui/Estados'
import { instalarAplicativo, PWA_ATIVO, useConviteInstalacao, useSituacaoInstalacao } from '../instalacao'

const VANTAGEM = 'Abra direto da tela inicial, como um aplicativo, e consulte a última leitura salva mesmo sem internet.'
const PASSOS_IOS = 'No iPhone ou iPad, toque em Compartilhar e depois em “Adicionar à Tela de Início”.'

/** Convite no Início, a partir da segunda visita e até ser dispensado (TC2 §9). */
export function ConviteInstalacao() {
  const { mostrar, situacao, dispensar } = useConviteInstalacao()
  if (!PWA_ATIVO || !mostrar) return null
  return (
    <Aviso tom="info" icone={Smartphone} titulo="Instale o Painel Aquícola">
      <p>{situacao === 'ios' ? `${VANTAGEM} ${PASSOS_IOS}` : VANTAGEM}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {situacao === 'disponivel' && (
          <Botao tamanho="sm" icone={Download} onClick={() => void instalarAplicativo()}>
            Instalar
          </Botao>
        )}
        <Botao tamanho="sm" variante="secundario" onClick={dispensar}>
          {situacao === 'ios' ? 'Entendi' : 'Agora não'}
        </Botao>
      </div>
    </Aviso>
  )
}

/** Cartão "Aplicativo" em Ajustes: sempre à mão, mesmo depois de dispensar o convite. */
export function CartaoAplicativo() {
  const situacao = useSituacaoInstalacao()
  if (!PWA_ATIVO) return null
  return (
    <Cartao aria-labelledby="titulo-aplicativo">
      <CabecalhoCartao id="titulo-aplicativo" titulo="Aplicativo" />
      {situacao === 'instalado' ? (
        <p className="text-sm text-tinta-suave">
          O Painel Aquícola está instalado neste aparelho. A última leitura salva fica disponível mesmo sem internet.
        </p>
      ) : (
        <div className="space-y-3 text-sm text-tinta-suave">
          <p>{VANTAGEM}</p>
          {situacao === 'disponivel' && (
            <Botao icone={Download} onClick={() => void instalarAplicativo()}>
              Instalar aplicativo
            </Botao>
          )}
          {situacao === 'ios' && <p>{PASSOS_IOS}</p>}
          {situacao === 'indisponivel' && (
            <p>Para instalar, use a opção “Instalar aplicativo” ou “Adicionar à tela inicial” do menu do navegador.</p>
          )}
        </div>
      )}
    </Cartao>
  )
}
