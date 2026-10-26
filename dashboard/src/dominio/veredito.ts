import { formatarHora, pluralizar } from '@/compartilhado/formatacao'
import type { Grandeza, NivelRisco } from './comum'
import type { PrevisaoAtual } from './entidades'
import { LIMITE_PREVISAO_MS } from './situacao'

export interface Veredito {
  tom: NivelRisco | 'indeterminado'
  titulo: string
  detalhe: string
  baixaConfianca: boolean
}

/**
 * Traduz a previsão já classificada pelo serviço de ML em uma frase direta.
 * Não reclassifica nada: o nível vem pronto da API.
 */
export function montarVeredito(
  previsao: PrevisaoAtual | undefined,
  rotulo: (g: Grandeza) => string,
  agora = Date.now(),
  motivoIndisponivel = 'Coletando dados. A previsão aparece quando houver leituras suficientes.',
): Veredito {
  const horizontes = [...(previsao?.horizontes ?? [])].sort((a, b) => a.horizonte_h - b.horizonte_h)
  const nivel = previsao?.nivel_risco ?? null

  if (previsao?.gerada_em && agora - Date.parse(previsao.gerada_em) > LIMITE_PREVISAO_MS) {
    return {
      tom: 'indeterminado',
      titulo: 'Previsão desatualizada',
      detalhe: `Última previsão às ${formatarHora(previsao.gerada_em)}. Faltam leituras recentes de pH e temperatura ou o serviço de previsão está parado.`,
      baixaConfianca: false,
    }
  }

  if (nivel === null || horizontes.length === 0) {
    return {
      tom: 'indeterminado',
      titulo: 'Previsão indisponível',
      detalhe: motivoIndisponivel,
      baixaConfianca: false,
    }
  }

  const baixaConfianca = Boolean(previsao?.od_atual?.baixa_confianca) || horizontes.some((h) => h.baixa_confianca)
  const ultimoHorizonte = horizontes[horizontes.length - 1]!.horizonte_h

  if (nivel === 'otimo') {
    const proximaMudanca = horizontes.find((h) => h.nivel_risco !== 'otimo')
    if (!proximaMudanca) {
      return {
        tom: 'otimo',
        titulo: 'Tudo na faixa ideal',
        detalhe: `Nenhuma ação necessária ${pluralizar(ultimoHorizonte, 'na próxima hora', `nas próximas ${ultimoHorizonte} horas`)}.`,
        baixaConfianca,
      }
    }
    return {
      tom: 'otimo',
      titulo: 'Na faixa ideal agora',
      detalhe: `${rotulo(proximaMudanca.parametro_critico)} pode sair da faixa ideal em cerca de ${proximaMudanca.horizonte_h} h.`,
      baixaConfianca,
    }
  }

  const foco = horizontes.find((h) => h.nivel_risco === nivel) ?? horizontes[0]!
  const parametro = rotulo(foco.parametro_critico)

  if (nivel === 'atencao') {
    return {
      tom: 'atencao',
      titulo: `${parametro} pede atenção`,
      detalhe: `Tendência de sair da faixa ideal em cerca de ${foco.horizonte_h} h.`,
      baixaConfianca,
    }
  }

  return {
    tom: 'critico',
    titulo: `${parametro} em nível crítico`,
    detalhe:
      foco.horizonte_h === 1
        ? 'Risco alto já na próxima hora. Veja as recomendações.'
        : `Risco alto em cerca de ${foco.horizonte_h} h. Veja as recomendações.`,
    baixaConfianca,
  }
}
