import { z } from 'zod'
import type { Grandeza, StatusSensor, StatusTanque, StatusAlerta, AcaoAtuador } from '@/dominio/comum'
import {
  acionamento,
  alertasPaginados,
  dispositivo,
  especie,
  eventosPaginados,
  previsaoAtual,
  respostaLeituras,
  sensor,
  tanque,
  type Bucket,
} from '@/dominio/entidades'
import { requisitar } from './cliente'

export interface DadosTanque {
  nome: string
  id_especie: number
  volume_litros: number
  quantidade_peixes: number
  data_povoamento: string | null
  status: StatusTanque
}

export interface DadosDispositivo {
  nome: string
  mac_address: string
  modelo_esp32: string
  versao_firmware: string | null
  ip_local: string | null
}

export const listarEspecies = (sinal?: AbortSignal) => requisitar('/especies', z.array(especie), { sinal })

export const listarTanques = (sinal?: AbortSignal) => requisitar('/tanques', z.array(tanque), { sinal })

export const buscarTanque = (id: number, sinal?: AbortSignal) => requisitar(`/tanques/${id}`, tanque, { sinal })

/** UC01: o dispositivo opcional é gravado na mesma transação do tanque. */
export const criarTanque = (dados: DadosTanque & { dispositivo?: DadosDispositivo }) =>
  requisitar('/tanques', tanque, { metodo: 'POST', corpo: dados })

export const atualizarTanque = (id: number, dados: DadosTanque) =>
  requisitar(`/tanques/${id}`, tanque, { metodo: 'PATCH', corpo: dados })

export const listarDispositivosDoTanque = (id: number, sinal?: AbortSignal) =>
  requisitar(`/tanques/${id}/dispositivos`, z.array(dispositivo), { sinal })

export const criarDispositivo = (dados: DadosDispositivo & { id_tanque: number }) =>
  requisitar('/dispositivos', dispositivo, { metodo: 'POST', corpo: dados })

export const atualizarDispositivo = (id: number, dados: DadosDispositivo) =>
  requisitar(`/dispositivos/${id}`, dispositivo, { metodo: 'PATCH', corpo: dados })

export const atualizarSensor = (id: number, status: StatusSensor) =>
  requisitar(`/sensores/${id}`, sensor, { metodo: 'PATCH', corpo: { status } })

export const comandarAerador = (idDispositivo: number, acao: AcaoAtuador) =>
  requisitar(`/dispositivos/${idDispositivo}/aerador`, acionamento, { metodo: 'POST', corpo: { acao } })

export interface FiltroLeituras {
  desde: Date
  ate: Date
  bucket: Bucket
  grandezas?: Grandeza[]
}

export const buscarLeituras = (idTanque: number, filtro: FiltroLeituras, sinal?: AbortSignal) =>
  requisitar(`/tanques/${idTanque}/leituras`, respostaLeituras, {
    sinal,
    parametros: {
      desde: filtro.desde.toISOString(),
      ate: filtro.ate.toISOString(),
      bucket: filtro.bucket,
      grandezas: filtro.grandezas?.join(','),
    },
  })

export const buscarPrevisaoAtual = (idTanque: number, sinal?: AbortSignal) =>
  requisitar(`/tanques/${idTanque}/previsoes/atual`, previsaoAtual, { sinal })

export interface FiltroAlertas {
  tanque?: number
  status?: StatusAlerta
  ativos?: boolean
  /** ISO 8601 — limita pela data de criação do alerta. */
  desde?: string
  ate?: string
  pagina?: number
  porPagina?: number
}

export const listarAlertas = (filtro: FiltroAlertas, sinal?: AbortSignal) =>
  requisitar('/alertas', alertasPaginados, {
    sinal,
    parametros: {
      tanque: filtro.tanque,
      status: filtro.status,
      ativos: filtro.ativos,
      desde: filtro.desde,
      ate: filtro.ate,
      pagina: filtro.pagina,
      por_pagina: filtro.porPagina,
    },
  })

export const listarEventos = (pagina: number, porPagina: number, sinal?: AbortSignal) =>
  requisitar('/eventos', eventosPaginados, { sinal, parametros: { pagina, por_pagina: porPagina } })
