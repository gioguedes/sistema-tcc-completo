import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Grandeza } from '@/dominio/comum'
import { rotuloGrandeza } from '@/dominio/grandezas'
import { lerPreferencias, salvarPreferencias, type Preferencias } from '@/infra/armazenamento/preferencias'
import { observarTema } from './tema'

interface ContextoPreferencias extends Preferencias {
  alterar: (parcial: Partial<Preferencias>) => void
}

const Contexto = createContext<ContextoPreferencias | null>(null)

export function ProvedorPreferencias({ children }: { children: ReactNode }) {
  const [preferencias, setPreferencias] = useState(lerPreferencias)

  const alterar = useCallback((parcial: Partial<Preferencias>) => {
    setPreferencias((atuais) => {
      const novas = { ...atuais, ...parcial }
      salvarPreferencias(novas)
      return novas
    })
  }, [])

  useEffect(() => observarTema(preferencias.tema), [preferencias.tema])

  const valor = useMemo(() => ({ ...preferencias, alterar }), [preferencias, alterar])
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}

export function usePreferencias() {
  const contexto = useContext(Contexto)
  if (!contexto) throw new Error('usePreferencias precisa estar dentro de <ProvedorPreferencias>')
  return contexto
}

/** Rótulo da grandeza conforme a preferência "Linguagem simples". */
export function useRotuloGrandeza() {
  const { linguagemSimples } = usePreferencias()
  return useCallback((g: Grandeza) => rotuloGrandeza(g, linguagemSimples), [linguagemSimples])
}
