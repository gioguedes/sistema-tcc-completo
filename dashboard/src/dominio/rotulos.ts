import type {
  CanalAlerta,
  NivelRisco,
  Perfil,
  StatusAlerta,
  StatusConexao,
  StatusSensor,
  StatusTanque,
} from './comum'

export const ROTULO_RISCO: Record<NivelRisco, string> = {
  otimo: 'Ótimo',
  atencao: 'Atenção',
  critico: 'Crítico',
}

/** Quanto maior, mais urgente. `null` significa previsão indisponível. */
export function severidade(nivel: NivelRisco | null): number {
  if (nivel === 'critico') return 3
  if (nivel === 'atencao') return 2
  if (nivel === 'otimo') return 1
  return 0
}

export const ROTULO_PERFIL: Record<Perfil, string> = {
  admin: 'Administrador',
  operador: 'Produtor',
}

export const ROTULO_STATUS_TANQUE: Record<StatusTanque, string> = {
  ativo: 'Ativo',
  manutencao: 'Em manutenção',
  inativo: 'Inativo',
}

export const ROTULO_STATUS_SENSOR: Record<StatusSensor, string> = {
  ativo: 'Ativo',
  inativo: 'Inativo',
  em_calibracao: 'Em calibração',
}

export const ROTULO_CONEXAO: Record<StatusConexao, string> = {
  online: 'Online',
  offline: 'Offline',
}

export const ROTULO_CANAL: Record<CanalAlerta, string> = {
  whatsapp: 'WhatsApp',
  email: 'e-mail',
  sms: 'SMS',
}

export const ROTULO_STATUS_ALERTA: Record<StatusAlerta, string> = {
  pendente: 'Envio pendente',
  enviado: 'Enviado',
  falha: 'Falha no envio',
}
