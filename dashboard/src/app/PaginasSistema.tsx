import { useRouteError } from 'react-router'
import { AlertTriangle, Compass, RotateCw } from 'lucide-react'
import { useTituloDocumento } from '@/compartilhado/hooks'
import { Botao, BotaoLink } from '@/ui/Botao'
import { EstadoVazio } from '@/ui/Estados'

export function PaginaNaoEncontrada() {
  useTituloDocumento('Página não encontrada')
  return (
    <EstadoVazio
      icone={Compass}
      titulo="Página não encontrada"
      descricao="O endereço pode estar incorreto ou a página foi movida."
      acao={<BotaoLink to="/">Voltar ao início</BotaoLink>}
      className="py-20"
    />
  )
}

/** Erro inesperado de renderização ou de carregamento de rota (ex.: nova versão publicada). */
export function PaginaErro() {
  const erro = useRouteError()
  useTituloDocumento('Algo deu errado')
  if (import.meta.env.DEV) console.error(erro)
  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <EstadoVazio
        icone={AlertTriangle}
        titulo="Algo deu errado"
        descricao="Não foi possível exibir esta tela. Recarregue a página; se o problema continuar, tente novamente mais tarde."
        acao={
          <Botao icone={RotateCw} onClick={() => window.location.reload()}>
            Recarregar
          </Botao>
        }
      />
    </main>
  )
}
