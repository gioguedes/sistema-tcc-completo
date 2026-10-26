export type TipoErro =
  | 'rede'
  | 'timeout'
  | 'sessao_expirada'
  | 'credenciais'
  | 'proibido'
  | 'nao_encontrado'
  | 'conflito'
  | 'validacao'
  | 'indisponivel'
  | 'servidor'
  | 'resposta_invalida'
  | 'desconhecido'

const MENSAGENS: Record<TipoErro, string> = {
  rede: 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.',
  timeout: 'O servidor demorou para responder. Tente novamente.',
  sessao_expirada: 'Sua sessão expirou. Entre novamente.',
  credenciais: 'E-mail ou senha incorretos.',
  proibido: 'Você não tem permissão para realizar esta ação.',
  nao_encontrado: 'Não encontramos o que você procurava.',
  conflito: 'Já existe um registro com esses dados.',
  validacao: 'Revise os campos destacados.',
  indisponivel: 'Esta função ainda não está disponível no servidor.',
  servidor: 'Ocorreu um erro no servidor. Tente novamente em instantes.',
  resposta_invalida: 'Recebemos uma resposta inesperada do servidor.',
  desconhecido: 'Algo deu errado. Tente novamente.',
}

export class ErroApi extends Error {
  readonly tipo: TipoErro
  readonly status?: number
  /** Mensagens por campo do formulário (422/409), já em português. */
  readonly campos: Record<string, string>

  constructor(tipo: TipoErro, status?: number, campos: Record<string, string> = {}) {
    super(MENSAGENS[tipo])
    this.name = 'ErroApi'
    this.tipo = tipo
    this.status = status
    this.campos = campos
  }
}

// Tipos de erro do Pydantic v2 mais comuns, caso o backend devolva a mensagem padrão em inglês.
const MENSAGENS_PYDANTIC: Record<string, string> = {
  missing: 'Campo obrigatório.',
  string_too_short: 'Campo obrigatório.',
  string_too_long: 'Texto maior que o permitido.',
  greater_than: 'Valor abaixo do permitido.',
  greater_than_equal: 'Valor abaixo do permitido.',
  less_than: 'Valor acima do permitido.',
  less_than_equal: 'Valor acima do permitido.',
  int_parsing: 'Informe um número inteiro.',
  float_parsing: 'Informe um número válido.',
  enum: 'Opção inválida.',
}

interface DetalheCampo {
  loc?: unknown[]
  msg?: string
  type?: string
}

/** Converte `{"detail": [{"loc": ["body", "campo"], "msg": "...", "type": "..."}]}` em `{campo: mensagem}`. */
function extrairCampos(detalhe: unknown): Record<string, string> {
  if (!Array.isArray(detalhe)) return {}
  const campos: Record<string, string> = {}
  for (const item of detalhe as DetalheCampo[]) {
    const caminho = (item.loc ?? []).filter((parte) => parte !== 'body').join('.')
    if (!caminho || campos[caminho]) continue
    const traduzida = item.type ? MENSAGENS_PYDANTIC[item.type] : undefined
    campos[caminho] = traduzida ?? item.msg ?? 'Valor inválido.'
  }
  return campos
}

export async function erroDeResposta(resposta: Response): Promise<ErroApi> {
  let detalhe: unknown
  try {
    detalhe = ((await resposta.json()) as { detail?: unknown })?.detail
  } catch {
    detalhe = undefined
  }
  const campos = extrairCampos(detalhe)
  const { status } = resposta

  if (status === 401) return new ErroApi('credenciais', status)
  if (status === 403) return new ErroApi('proibido', status)
  if (status === 404) return new ErroApi('nao_encontrado', status)
  if (status === 409) return new ErroApi('conflito', status, campos)
  if (status === 400 || status === 422) return new ErroApi('validacao', status, campos)
  if (status === 408 || status === 504) return new ErroApi('timeout', status)
  // 501: rota do contrato que a versão atual da API ainda não implementa
  if (status === 501) return new ErroApi('indisponivel', status)
  if (status >= 500) return new ErroApi('servidor', status)
  return new ErroApi('desconhecido', status)
}

export function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : MENSAGENS.desconhecido
}

export function ehErroApi(erro: unknown, tipo?: TipoErro): erro is ErroApi {
  return erro instanceof ErroApi && (tipo === undefined || erro.tipo === tipo)
}
