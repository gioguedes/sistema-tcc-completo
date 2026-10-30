/** Tema escuro opcional (TC2 §8): "automatico" segue a preferência do sistema. */
export type Tema = 'automatico' | 'claro' | 'escuro'

export interface Preferencias {
  /** Mostra faixas ideais, confiança da previsão e detalhes técnicos dos dispositivos. */
  modoAvancado: boolean
  /** Troca termos técnicos por explicações do dia a dia. */
  linguagemSimples: boolean
  explicacaoOdDispensada: boolean
  /** Claro, escuro ou o do sistema (TC2 §8: o claro é o padrão de uso sob sol; o escuro é opcional). */
  tema: Tema
  /** Menu lateral do computador reduzido aos ícones. */
  menuRecolhido: boolean
  /** Altitude do local em metros: corrige o OD de saturação pela pressão do ar. */
  altitudeM: number
}

const CHAVE = 'painel-aquicola:preferencias'

export const PREFERENCIAS_PADRAO: Preferencias = {
  modoAvancado: false,
  linguagemSimples: false,
  explicacaoOdDispensada: false,
  tema: 'automatico',
  menuRecolhido: false,
  // altitude de São Paulo, onde está o protótipo
  altitudeM: 760,
}

// Preferência de interface por aparelho: o armazenamento pode falhar (aba anônima) sem quebrar a tela.
export function lerPreferencias(): Preferencias {
  try {
    const salvo = localStorage.getItem(CHAVE)
    return salvo ? { ...PREFERENCIAS_PADRAO, ...(JSON.parse(salvo) as Partial<Preferencias>) } : PREFERENCIAS_PADRAO
  } catch {
    return PREFERENCIAS_PADRAO
  }
}

export function salvarPreferencias(preferencias: Preferencias) {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(preferencias))
  } catch {
    // segue funcionando só nesta sessão
  }
}
