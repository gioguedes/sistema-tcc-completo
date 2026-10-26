import { z } from 'zod'
import { statusTanque } from './comum'

const REGEX_MAC = /^([0-9a-f]{2}[:-]?){5}[0-9a-f]{2}$/i
const REGEX_IPV4 = /^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$/

/** Mesmo formato gravado pela ingestão MQTT (`aa:bb:cc:dd:ee:ff`), para que a leitura encontre o dispositivo. */
export function normalizarMac(valor: string): string {
  const hex = valor.replace(/[^0-9a-f]/gi, '').toLowerCase()
  return hex.match(/.{1,2}/g)?.join(':') ?? hex
}

/** Aceita "(11) 98765-4321", "11987654321" ou "+55 11 98765-4321"; devolve "+5511987654321". */
export function normalizarTelefone(valor: string): string | null {
  let digitos = valor.replace(/\D/g, '')
  if (digitos.length === 10 || digitos.length === 11) digitos = `55${digitos}`
  if (!digitos.startsWith('55') || (digitos.length !== 12 && digitos.length !== 13)) return null
  return `+${digitos}`
}

export function formatarTelefone(valor: string | null): string {
  if (!valor) return ''
  const digitos = valor.replace(/\D/g, '').replace(/^55/, '')
  const ddd = digitos.slice(0, 2)
  const numero = digitos.slice(2)
  const meio = numero.length === 9 ? 5 : 4
  return `(${ddd}) ${numero.slice(0, meio)}-${numero.slice(meio)}`
}

function hojeLocal(): string {
  const agora = new Date()
  const mes = String(agora.getMonth() + 1).padStart(2, '0')
  const dia = String(agora.getDate()).padStart(2, '0')
  return `${agora.getFullYear()}-${mes}-${dia}`
}

export const esquemaLogin = z.object({
  email: z.string().trim().min(1, 'Informe seu e-mail.').pipe(z.email('Informe um e-mail válido.')),
  senha: z.string().min(1, 'Informe sua senha.'),
  lembrar: z.boolean(),
})

// Regras espelham os CHECKs do banco e o UC01; a validação definitiva continua no backend.
export const esquemaTanque = z.object({
  nome: z.string().trim().min(1, 'Informe o nome do tanque.').max(120, 'Use no máximo 120 caracteres.'),
  id_especie: z.number({ error: 'Selecione a espécie.' }).int().positive('Selecione a espécie.'),
  volume_litros: z
    .number({ error: 'Informe o volume em litros.' })
    .gt(0, 'O volume deve ser maior que zero.')
    .max(999_999.99, 'Volume acima do limite permitido.'),
  quantidade_peixes: z
    .number({ error: 'Informe a quantidade de peixes.' })
    .int('Use um número inteiro.')
    .min(0, 'A quantidade não pode ser negativa.'),
  data_povoamento: z.string().refine((v) => v === '' || v <= hojeLocal(), 'A data não pode estar no futuro.'),
  status: statusTanque,
})

export const esquemaDispositivo = z.object({
  nome: z.string().trim().min(1, 'Informe o nome do dispositivo.').max(120, 'Use no máximo 120 caracteres.'),
  mac_address: z
    .string()
    .trim()
    .min(1, 'Informe o endereço MAC do ESP32.')
    .regex(REGEX_MAC, 'Use o formato AA:BB:CC:DD:EE:FF.')
    .transform(normalizarMac),
  modelo_esp32: z.string().trim().min(1, 'Informe o modelo.').max(60, 'Use no máximo 60 caracteres.'),
  versao_firmware: z.string().trim().max(30, 'Use no máximo 30 caracteres.'),
  ip_local: z
    .string()
    .trim()
    .refine((v) => v === '' || REGEX_IPV4.test(v), 'Informe um IP válido, como 192.168.0.20.'),
})

const rascunhoDispositivo = z.object({
  nome: z.string(),
  mac_address: z.string(),
  modelo_esp32: z.string(),
  versao_firmware: z.string(),
  ip_local: z.string(),
})

/** UC01: o tanque e, opcionalmente, o dispositivo associado pelo MAC, gravados juntos. */
export const esquemaCadastroTanque = esquemaTanque
  .extend({ associar_dispositivo: z.boolean(), dispositivo: rascunhoDispositivo })
  .superRefine(
    (valores, ctx) => {
      if (!valores?.associar_dispositivo) return
      const resultado = esquemaDispositivo.safeParse(valores.dispositivo)
      if (resultado.success) return
      for (const problema of resultado.error.issues) {
        ctx.addIssue({ code: 'custom', message: problema.message, path: ['dispositivo', ...problema.path] })
      }
    },
    // Valida o dispositivo mesmo quando os campos do tanque têm erro: todos os problemas aparecem de uma vez.
    { when: () => true },
  )

export const esquemaConta = z.object({
  nome: z.string().trim().min(1, 'Informe seu nome.').max(120, 'Use no máximo 120 caracteres.'),
  telefone: z
    .string()
    .trim()
    .refine((v) => v === '' || normalizarTelefone(v) !== null, 'Informe DDD e número, como (11) 98765-4321.'),
})

export type ValoresLogin = z.infer<typeof esquemaLogin>
export type ValoresTanque = z.infer<typeof esquemaTanque>
export type ValoresCadastroTanque = z.infer<typeof esquemaCadastroTanque>
export type EntradaDispositivo = z.input<typeof esquemaDispositivo>
export type ValoresDispositivo = z.output<typeof esquemaDispositivo>
export type ValoresConta = z.infer<typeof esquemaConta>
