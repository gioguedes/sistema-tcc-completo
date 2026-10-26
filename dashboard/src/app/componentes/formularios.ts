import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import type { ValoresDispositivo } from '@/dominio/formularios'
import { ErroApi, mensagemDeErro } from '@/infra/api/erros'
import type { DadosDispositivo } from '@/infra/api/recursos'

/**
 * Leva os erros por campo da API (422/409) para os campos do formulário.
 * Devolve a mensagem geral quando o erro não pertence a um campo específico.
 */
export function aplicarErrosDaApi<T extends FieldValues>(erro: unknown, setError: UseFormSetError<T>): string | null {
  if (erro instanceof ErroApi && Object.keys(erro.campos).length > 0) {
    Object.entries(erro.campos).forEach(([campo, mensagem], indice) => {
      setError(campo as Path<T>, { type: 'servidor', message: mensagem }, { shouldFocus: indice === 0 })
    })
    return null
  }
  return mensagemDeErro(erro)
}

export function paraDadosDispositivo(valores: ValoresDispositivo): DadosDispositivo {
  return {
    nome: valores.nome,
    mac_address: valores.mac_address,
    modelo_esp32: valores.modelo_esp32,
    versao_firmware: valores.versao_firmware || null,
    ip_local: valores.ip_local || null,
  }
}

/** Converte o valor de <select>/<input type=number> vazio em NaN, que o Zod rejeita com a mensagem do campo. */
export const comoNumero = (valor: unknown) => (valor === '' || valor === null || valor === undefined ? Number.NaN : Number(valor))
