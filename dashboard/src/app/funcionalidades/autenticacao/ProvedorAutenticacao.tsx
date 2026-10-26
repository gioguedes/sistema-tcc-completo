import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Usuario } from '@/dominio/entidades'
import { buscarUsuarioAtual, entrar, sair } from '@/infra/api/autenticacao'
import { ehErroApi } from '@/infra/api/erros'
import { sessao } from '@/infra/api/sessao'
import { apagarDadosLocais } from '@/infra/armazenamento/ultimaLeitura'
import { INTERVALO_ATUALIZACAO_MS } from '../../consultas/cliente'

type EstadoSessao =
  | { status: 'verificando' }
  | { status: 'anonimo'; expirada?: boolean }
  | { status: 'autenticado'; usuario: Usuario }
  /** Não foi possível falar com o servidor ao abrir o app: a sessão pode estar válida, mas não dá para conferir. */
  | { status: 'sem_conexao' }

interface ContextoAutenticacao {
  estado: EstadoSessao
  entrar: (dados: { email: string; senha: string; lembrar: boolean }) => Promise<void>
  sair: () => Promise<void>
  atualizarUsuario: (usuario: Usuario) => void
  /** Nova tentativa de restaurar a sessão depois de "sem_conexao". */
  tentarNovamente: () => void
}

const Contexto = createContext<ContextoAutenticacao | null>(null)

/** Ao abrir o app, tenta restaurar a sessão pelo cookie de renovação (o token não fica salvo no navegador). */
async function restaurarSessao(): Promise<EstadoSessao> {
  const resultado = await sessao.restaurar()
  if (resultado === 'sem_conexao') return { status: 'sem_conexao' }
  if (resultado === 'sem_sessao') {
    // sessão encerrada em definitivo: a cópia offline da conta anterior não deve ficar no aparelho
    void apagarDadosLocais()
    return { status: 'anonimo' }
  }
  try {
    return { status: 'autenticado', usuario: await buscarUsuarioAtual() }
  } catch (erro) {
    return ehErroApi(erro, 'rede') || ehErroApi(erro, 'timeout') ? { status: 'sem_conexao' } : { status: 'anonimo' }
  }
}

export function ProvedorAutenticacao({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [estado, setEstado] = useState<EstadoSessao>({ status: 'verificando' })
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    let ativo = true
    void restaurarSessao().then((novo) => {
      if (ativo) setEstado(novo)
    })
    return () => {
      ativo = false
    }
  }, [tentativa])

  // Sem conexão na abertura: tenta de novo assim que a rede volta e, com o servidor fora, no ritmo da sondagem.
  useEffect(() => {
    if (estado.status !== 'sem_conexao') return
    const novaTentativa = () => setTentativa((n) => n + 1)
    window.addEventListener('online', novaTentativa)
    const intervalo = window.setInterval(novaTentativa, INTERVALO_ATUALIZACAO_MS)
    return () => {
      window.removeEventListener('online', novaTentativa)
      window.clearInterval(intervalo)
    }
  }, [estado.status])

  useEffect(
    () =>
      sessao.aoExpirar(() => {
        queryClient.clear()
        void apagarDadosLocais()
        setEstado({ status: 'anonimo', expirada: true })
      }),
    [queryClient],
  )

  const tentarNovamente = useCallback(() => {
    setEstado({ status: 'verificando' })
    setTentativa((n) => n + 1)
  }, [])

  const fazerLogin = useCallback(async (dados: { email: string; senha: string; lembrar: boolean }) => {
    await entrar(dados)
    const usuario = await buscarUsuarioAtual()
    setEstado({ status: 'autenticado', usuario })
  }, [])

  const fazerLogout = useCallback(async () => {
    try {
      await sair()
    } catch {
      // Mesmo sem resposta do servidor, a sessão local é encerrada.
    } finally {
      queryClient.clear()
      await apagarDadosLocais()
      setEstado({ status: 'anonimo' })
    }
  }, [queryClient])

  const atualizarUsuario = useCallback((usuario: Usuario) => setEstado({ status: 'autenticado', usuario }), [])

  const valor = useMemo(
    () => ({ estado, entrar: fazerLogin, sair: fazerLogout, atualizarUsuario, tentarNovamente }),
    [estado, fazerLogin, fazerLogout, atualizarUsuario, tentarNovamente],
  )
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}

export function useAutenticacao() {
  const contexto = useContext(Contexto)
  if (!contexto) throw new Error('useAutenticacao precisa estar dentro de <ProvedorAutenticacao>')
  return contexto
}

/** Usuário logado — só use dentro de rotas protegidas. */
export function useUsuario(): Usuario {
  const { estado } = useAutenticacao()
  if (estado.status !== 'autenticado') throw new Error('useUsuario usado fora de uma rota protegida')
  return estado.usuario
}
