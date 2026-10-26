import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { Lock } from 'lucide-react'
import { useTituloDocumento } from '@/compartilhado/hooks'
import { BotaoLink } from '@/ui/Botao'
import { Carregando, EstadoVazio } from '@/ui/Estados'
import { useAutenticacao, useUsuario } from './ProvedorAutenticacao'
import { TelaSemConexao } from './TelaSemConexao'

export function TelaCarregamento() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <Carregando texto="Carregando o Painel Aquícola…" />
    </div>
  )
}

export function RotaProtegida({ children }: { children: ReactNode }) {
  const { estado } = useAutenticacao()
  const local = useLocation()
  if (estado.status === 'verificando') return <TelaCarregamento />
  if (estado.status === 'sem_conexao') return <TelaSemConexao />
  if (estado.status === 'anonimo') {
    return <Navigate to="/entrar" replace state={{ destino: `${local.pathname}${local.search}` }} />
  }
  return children
}

/** Conveniência de interface: quem autoriza de fato é o backend (403). */
export function SomenteAdmin({ children }: { children: ReactNode }) {
  const usuario = useUsuario()
  if (usuario.perfil !== 'admin') return <AcessoRestrito />
  return children
}

export function AcessoRestrito() {
  useTituloDocumento('Acesso restrito')
  return (
    <EstadoVazio
      icone={Lock}
      titulo="Acesso restrito"
      descricao="Esta área é exclusiva para administradores. Se precisar cadastrar ou alterar tanques, fale com o administrador do sistema."
      acao={<BotaoLink to="/" variante="secundario">Voltar ao início</BotaoLink>}
      className="py-16"
    />
  )
}
