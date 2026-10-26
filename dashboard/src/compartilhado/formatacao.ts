const LOCALE = 'pt-BR'

const formatadoresNumero = new Map<number, Intl.NumberFormat>()

export function formatarNumero(valor: number, casas = 1): string {
  let formatador = formatadoresNumero.get(casas)
  if (!formatador) {
    formatador = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: casas, maximumFractionDigits: casas })
    formatadoresNumero.set(casas, formatador)
  }
  return formatador.format(valor)
}

const formatoHora = new Intl.DateTimeFormat(LOCALE, { hour: '2-digit', minute: '2-digit' })
const formatoData = new Intl.DateTimeFormat(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric' })
const formatoDiaMes = new Intl.DateTimeFormat(LOCALE, { day: '2-digit', month: '2-digit' })

const paraData = (valor: string | number | Date) => (valor instanceof Date ? valor : new Date(valor))

export const formatarHora = (valor: string | number | Date) => formatoHora.format(paraData(valor))
export const formatarData = (valor: string | number | Date) => formatoData.format(paraData(valor))
export const formatarDiaMes = (valor: string | number | Date) => formatoDiaMes.format(paraData(valor))
export const formatarDataHora = (valor: string | number | Date) =>
  `${formatarData(valor)} às ${formatarHora(valor)}`

function inicioDoDia(data: Date): number {
  return new Date(data.getFullYear(), data.getMonth(), data.getDate()).getTime()
}

/** "Hoje", "Ontem" ou a data — usado para agrupar listas por dia. */
export function rotuloDia(valor: string | number | Date, agora = Date.now()): string {
  const diferencaDias = Math.round((inicioDoDia(new Date(agora)) - inicioDoDia(paraData(valor))) / 86_400_000)
  if (diferencaDias === 0) return 'Hoje'
  if (diferencaDias === 1) return 'Ontem'
  return formatarData(valor)
}

/** "02:40" para hoje, "Ontem 22:30" ou "05/10 18:12" para dias anteriores. */
export function formatarMomento(valor: string | number | Date, agora = Date.now()): string {
  const dia = rotuloDia(valor, agora)
  if (dia === 'Hoje') return formatarHora(valor)
  if (dia === 'Ontem') return `Ontem ${formatarHora(valor)}`
  return `${formatarDiaMes(valor)} ${formatarHora(valor)}`
}

/** "agora", "há 3 min", "há 2 h", "há 4 dias". */
export function tempoRelativo(valor: string | number | Date, agora = Date.now()): string {
  const segundos = Math.max(0, Math.round((agora - paraData(valor).getTime()) / 1000))
  if (segundos < 60) return 'agora'
  const minutos = Math.floor(segundos / 60)
  if (minutos < 60) return `há ${minutos} min`
  const horas = Math.floor(minutos / 60)
  if (horas < 24) return `há ${horas} h`
  const dias = Math.floor(horas / 24)
  return dias === 1 ? 'há 1 dia' : `há ${dias} dias`
}

export function primeiroNome(nome: string): string {
  return nome.trim().split(/\s+/)[0] ?? nome
}

export function saudacao(agora = new Date()): string {
  const hora = agora.getHours()
  if (hora < 5 || hora >= 18) return 'Boa noite'
  if (hora < 12) return 'Bom dia'
  return 'Boa tarde'
}

export function pluralizar(quantidade: number, singular: string, plural: string): string {
  return quantidade === 1 ? singular : plural
}
