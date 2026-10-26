import {
  criarDadosIniciais,
  USUARIOS_INICIAIS,
  type AcionamentoSimulado,
  type DispositivoSimulado,
  type SensorSimulado,
  type TanqueSimulado,
  type UsuarioSimulado,
} from './dados'

/**
 * "Banco" do servidor simulado. Persistido no localStorage para que cadastros
 * feitos na demonstração sobrevivam ao recarregar a página.
 */
export interface BancoSimulado {
  versao: number
  usuarios: UsuarioSimulado[]
  tanques: TanqueSimulado[]
  dispositivos: DispositivoSimulado[]
  sensores: SensorSimulado[]
  acionamentos: AcionamentoSimulado[]
}

const CHAVE_BANCO = 'painel-aquicola:banco-simulado'
const CHAVE_SESSAO = 'painel-aquicola:sessao-simulada'
const VERSAO = 2

let banco: BancoSimulado | null = null

function criarBanco(): BancoSimulado {
  return {
    versao: VERSAO,
    usuarios: structuredClone(USUARIOS_INICIAIS),
    ...criarDadosIniciais(Date.now()),
    acionamentos: [],
  }
}

function carregar(): BancoSimulado | null {
  try {
    const salvo = localStorage.getItem(CHAVE_BANCO)
    if (!salvo) return null
    const dados = JSON.parse(salvo) as BancoSimulado
    return dados.versao === VERSAO ? dados : null
  } catch {
    return null
  }
}

export function obterBanco(): BancoSimulado {
  banco ??= carregar() ?? criarBanco()
  return banco
}

export function salvarBanco() {
  try {
    localStorage.setItem(CHAVE_BANCO, JSON.stringify(obterBanco()))
  } catch {
    // Sem armazenamento disponível: os dados simulados ficam só em memória.
  }
}

export function resetarBanco() {
  banco = criarBanco()
  salvarBanco()
  encerrarSessao()
}

export function proximoId(registros: { id: number }[]): number {
  return registros.reduce((maior, r) => Math.max(maior, r.id), 0) + 1
}

// O cookie HttpOnly de renovação é simulado aqui: "lembrar de mim" persiste; sem ele, dura a aba.
export function abrirSessao(idUsuario: number, lembrar: boolean) {
  encerrarSessao()
  try {
    ;(lembrar ? localStorage : sessionStorage).setItem(CHAVE_SESSAO, String(idUsuario))
  } catch {
    // ignora: a sessão simulada só não sobreviverá ao recarregamento
  }
}

export function lerSessao(): number | null {
  try {
    const valor = localStorage.getItem(CHAVE_SESSAO) ?? sessionStorage.getItem(CHAVE_SESSAO)
    return valor ? Number(valor) : null
  } catch {
    return null
  }
}

export function encerrarSessao() {
  try {
    localStorage.removeItem(CHAVE_SESSAO)
    sessionStorage.removeItem(CHAVE_SESSAO)
  } catch {
    // ignora
  }
}
