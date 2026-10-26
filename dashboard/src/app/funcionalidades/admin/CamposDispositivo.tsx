import type { FieldErrors, UseFormRegisterReturn } from 'react-hook-form'
import type { EntradaDispositivo } from '@/dominio/formularios'
import { Campo } from '@/ui/Campos'

interface PropsCamposDispositivo {
  /** Registra o campo no formulário de quem usa (no cadastro do tanque, os campos ficam em "dispositivo."). */
  campo: (nome: keyof EntradaDispositivo) => UseFormRegisterReturn
  erros: FieldErrors<EntradaDispositivo> | undefined
}

export function CamposDispositivo({ campo, erros }: PropsCamposDispositivo) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Campo rotulo="Nome do dispositivo" obrigatorio placeholder="Ex.: Nó sensor Norte" erro={erros?.nome?.message} {...campo('nome')} />
      <Campo
        rotulo="Endereço MAC do ESP32"
        obrigatorio
        placeholder="AA:BB:CC:DD:EE:FF"
        autoCapitalize="characters"
        spellCheck={false}
        dica="Impresso na etiqueta da placa ou exibido pelo firmware ao ligar."
        erro={erros?.mac_address?.message}
        {...campo('mac_address')}
      />
      <Campo rotulo="Modelo da placa" obrigatorio erro={erros?.modelo_esp32?.message} {...campo('modelo_esp32')} />
      <Campo rotulo="Versão do firmware" placeholder="Ex.: 1.2.0" dica="Opcional." erro={erros?.versao_firmware?.message} {...campo('versao_firmware')} />
      <Campo
        rotulo="IP local"
        placeholder="Ex.: 192.168.0.20"
        inputMode="decimal"
        dica="Opcional."
        erro={erros?.ip_local?.message}
        {...campo('ip_local')}
      />
    </div>
  )
}

export const DISPOSITIVO_VAZIO: EntradaDispositivo = {
  nome: '',
  mac_address: '',
  modelo_esp32: 'ESP32 DevKitC V4',
  versao_firmware: '',
  ip_local: '',
}
