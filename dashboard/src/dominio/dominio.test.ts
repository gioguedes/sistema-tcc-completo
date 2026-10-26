import { escolherBucket, periodoDaUrl } from '@/compartilhado/periodo'
import type { PrevisaoAtual } from './entidades'
import { esquemaCadastroTanque, esquemaTanque, normalizarMac, normalizarTelefone } from './formularios'
import { formatarFaixa, faixaIdealDe, rotuloGrandeza } from './grandezas'
import { leituraAtrasada } from './situacao'
import { montarVeredito } from './veredito'

const rotulo = (g: Parameters<typeof rotuloGrandeza>[0]) => rotuloGrandeza(g)

function previsao(nivel: PrevisaoAtual['nivel_risco'], niveis: ('otimo' | 'atencao' | 'critico')[], baixa = false): PrevisaoAtual {
  return {
    id_tanque: 1,
    nivel_risco: nivel,
    gerada_em: nivel === null ? null : '2026-10-07T03:00:00Z',
    od_atual: null,
    horizontes: niveis.map((n, i) => ({
      id: i + 1,
      parametro_critico: 'od',
      valor_previsto: 3,
      nivel_risco: n,
      horizonte_h: i + 1,
      confianca: 0.8,
      baixa_confianca: baixa && i === niveis.length - 1,
      ts_previsao: '2026-10-07T03:00:00Z',
    })),
  }
}

// Lado da apresentação do CT05: cada nível vindo do ML vira a mensagem e o tom corretos.
describe('veredito da previsão', () => {
  it('sem previsão, informa que está coletando dados (não inventa classificação)', () => {
    expect(montarVeredito(undefined, rotulo).tom).toBe('indeterminado')
    expect(montarVeredito(previsao(null, []), rotulo).titulo).toBe('Previsão indisponível')
  })

  it('tudo ótimo nas 3 horas', () => {
    const v = montarVeredito(previsao('otimo', ['otimo', 'otimo', 'otimo']), rotulo, Date.parse('2026-10-07T03:01:00Z'))
    expect(v).toMatchObject({ tom: 'otimo', titulo: 'Tudo na faixa ideal', detalhe: 'Nenhuma ação necessária nas próximas 3 horas.' })
  })

  it('ótimo agora, mas avisa a mudança prevista', () => {
    const v = montarVeredito(previsao('otimo', ['otimo', 'atencao', 'atencao']), rotulo, Date.parse('2026-10-07T03:01:00Z'))
    expect(v.detalhe).toBe('Oxigênio (estimado) pode sair da faixa ideal em cerca de 2 h.')
  })

  it('previsão sem linha nova há mais de 3 ciclos do ML vira "desatualizada"', () => {
    const agora = Date.parse('2026-10-07T03:20:00Z')
    const v = montarVeredito(previsao('otimo', ['otimo', 'otimo', 'otimo']), rotulo, agora)
    expect(v).toMatchObject({ tom: 'indeterminado', titulo: 'Previsão desatualizada' })
    expect(montarVeredito(previsao('otimo', ['otimo', 'otimo', 'otimo']), rotulo, agora - 10 * 60_000).tom).toBe('otimo')
  })

  it('OD estimado (h = 0) com confiança baixa marca o veredito', () => {
    const p = { ...previsao('atencao', ['atencao', 'atencao', 'atencao']), od_atual: { valor: 4.2, nivel_risco: 'atencao' as const, confianca: 0.46, baixa_confianca: true } }
    expect(montarVeredito(p, rotulo, Date.parse('2026-10-07T03:01:00Z')).baixaConfianca).toBe(true)
  })

  it('crítico na primeira hora, com indicador de baixa confiança', () => {
    const v = montarVeredito(previsao('critico', ['critico', 'critico', 'critico'], true), rotulo, Date.parse('2026-10-07T03:01:00Z'))
    expect(v).toMatchObject({ tom: 'critico', titulo: 'Oxigênio (estimado) em nível crítico', baixaConfianca: true })
    expect(v.detalhe).toContain('próxima hora')
  })
})

describe('validações do UC01', () => {
  const tanqueValido = { nome: 'Tanque A', id_especie: 1, volume_litros: 80, quantidade_peixes: 5, data_povoamento: '', status: 'ativo' as const }

  it('exige volume maior que zero', () => {
    const r = esquemaTanque.safeParse({ ...tanqueValido, volume_litros: 0 })
    expect(r.success).toBe(false)
    expect(r.error?.issues[0]?.message).toBe('O volume deve ser maior que zero.')
  })

  it('não aceita data de povoamento no futuro', () => {
    expect(esquemaTanque.safeParse({ ...tanqueValido, data_povoamento: '2999-01-01' }).success).toBe(false)
  })

  it('valida o dispositivo só quando ele é associado, junto com os erros do tanque', () => {
    const dispositivoVazio = { nome: '', mac_address: '', modelo_esp32: 'ESP32 DevKitC V4', versao_firmware: '', ip_local: '' }
    const sem = esquemaCadastroTanque.safeParse({ ...tanqueValido, associar_dispositivo: false, dispositivo: dispositivoVazio })
    expect(sem.success).toBe(true)
    const com = esquemaCadastroTanque.safeParse({ ...tanqueValido, nome: '', associar_dispositivo: true, dispositivo: dispositivoVazio })
    const caminhos = com.error?.issues.map((i) => i.path.join('.'))
    expect(caminhos).toEqual(expect.arrayContaining(['nome', 'dispositivo.nome', 'dispositivo.mac_address']))
  })

  it('normaliza o MAC no mesmo formato usado pela ingestão MQTT', () => {
    expect(normalizarMac('A4F00F643C70')).toBe('a4:f0:0f:64:3c:70')
    expect(normalizarMac('a4-f0-0f-64-3c-70')).toBe('a4:f0:0f:64:3c:70')
  })

  it('normaliza telefone brasileiro para o formato internacional', () => {
    expect(normalizarTelefone('(11) 98765-4321')).toBe('+5511987654321')
    expect(normalizarTelefone('+55 11 3456-7890')).toBe('+551134567890')
    expect(normalizarTelefone('1234')).toBeNull()
  })
})

describe('período e agregação (RNF02)', () => {
  const h = 3_600_000
  const agora = new Date('2026-10-07T12:00:00Z')
  it('usa dados brutos só em janelas curtas e médias nas longas', () => {
    expect(escolherBucket(new Date(agora.getTime() - 3 * h), agora)).toBe('raw')
    expect(escolherBucket(new Date(agora.getTime() - 24 * h), agora)).toBe('5m')
    expect(escolherBucket(new Date(agora.getTime() - 30 * 24 * h), agora)).toBe('1h')
  })

  it('lê o período da URL e ignora valores inválidos', () => {
    expect(periodoDaUrl(new URLSearchParams('periodo=7d'))).toEqual({ tipo: 'relativo', chave: '7d' })
    expect(periodoDaUrl(new URLSearchParams('periodo=qualquer'))).toEqual({ tipo: 'relativo', chave: '24h' })
    expect(periodoDaUrl(new URLSearchParams('periodo=personalizado&desde=2026-10-05&ate=2026-10-01'))).toEqual({
      tipo: 'relativo',
      chave: '24h',
    })
  })
})

describe('atualizações do backend (09/10)', () => {
  const tilapia = { id: 1, nome_comum: 'Tilápia', nome_cientifico: 'O. niloticus', ph_min: 6.5, ph_max: 8.5, temp_min: 20, temp_max: 30, od_min: 4, od_max: 8 }

  it('OD não tem limite superior de risco (regra corrigida do ML)', () => {
    expect(faixaIdealDe('od', tilapia)).toEqual({ min: 4, max: null })
    expect(formatarFaixa('od', { min: 4, max: null })).toBe('a partir de 4,0 mg/L')
    expect(formatarFaixa('ph', { min: 6.5, max: 8.5 })).toBe('6,5–8,5')
  })

  it('sensor em falha: a grandeza que ficou para trás das outras é marcada', () => {
    const ultima = '2026-10-07T03:20:00Z'
    const leitura = (ts: string, estimado = false) => ({ grandeza: 'turbidez' as const, valor: 10, unidade: 'NTU', ts, estimado, baixa_confianca: false })
    expect(leituraAtrasada(leitura('2026-10-07T03:19:00Z'), ultima)).toBe(false)
    expect(leituraAtrasada(leitura('2026-10-07T03:08:00Z'), ultima)).toBe(true)
    // o OD estimado segue o ciclo de 5 min do ML: só fica atrasado após 15 min
    expect(leituraAtrasada(leitura('2026-10-07T03:10:00Z', true), ultima)).toBe(false)
    expect(leituraAtrasada(leitura('2026-10-07T03:00:00Z', true), ultima)).toBe(true)
  })
})
