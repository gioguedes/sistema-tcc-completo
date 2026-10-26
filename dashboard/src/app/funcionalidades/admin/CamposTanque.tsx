import type { FieldErrors, RegisterOptions, UseFormRegisterReturn } from 'react-hook-form'
import type { Especie } from '@/dominio/entidades'
import type { ValoresTanque } from '@/dominio/formularios'
import { ROTULO_STATUS_TANQUE } from '@/dominio/rotulos'
import { Campo, Selecao } from '@/ui/Campos'
import { comoNumero } from '../../componentes/formularios'

interface PropsCamposTanque {
  /** Registra o campo no formulário de quem usa (cadastro e edição estendem ValoresTanque). */
  campo: (nome: keyof ValoresTanque, opcoes?: Pick<RegisterOptions, 'setValueAs'>) => UseFormRegisterReturn
  erros: FieldErrors<ValoresTanque>
  especies: Especie[] | undefined
  carregandoEspecies: boolean
}

export function CamposTanque({ campo, erros, especies, carregandoEspecies }: PropsCamposTanque) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Campo
        rotulo="Nome do tanque"
        obrigatorio
        placeholder="Ex.: Tanque Norte"
        maxLength={120}
        erro={erros.nome?.message}
        className="sm:col-span-2"
        {...campo('nome')}
      />
      <Selecao
        rotulo="Espécie"
        obrigatorio
        disabled={carregandoEspecies}
        dica="As faixas ideais de pH, temperatura e oxigênio vêm da espécie."
        erro={erros.id_especie?.message}
        {...campo('id_especie', { setValueAs: comoNumero })}
      >
        <option value="">{carregandoEspecies ? 'Carregando…' : 'Selecione'}</option>
        {especies?.map((e) => (
          <option key={e.id} value={e.id}>
            {e.nome_comum} ({e.nome_cientifico})
          </option>
        ))}
      </Selecao>
      <Campo
        rotulo="Volume"
        obrigatorio
        type="number"
        inputMode="decimal"
        min={0}
        step="0.01"
        sufixo="litros"
        erro={erros.volume_litros?.message}
        {...campo('volume_litros', { setValueAs: comoNumero })}
      />
      <Campo
        rotulo="Quantidade de peixes"
        obrigatorio
        type="number"
        inputMode="numeric"
        min={0}
        step="1"
        erro={erros.quantidade_peixes?.message}
        {...campo('quantidade_peixes', { setValueAs: comoNumero })}
      />
      <Campo
        rotulo="Data de povoamento"
        type="date"
        dica="Opcional."
        erro={erros.data_povoamento?.message}
        {...campo('data_povoamento')}
      />
      <Selecao
        rotulo="Situação do tanque"
        dica="Para deixar de monitorar, marque como Inativo. O histórico de leituras é preservado."
        erro={erros.status?.message}
        className="sm:col-span-2"
        {...campo('status')}
      >
        {Object.entries(ROTULO_STATUS_TANQUE).map(([valor, rotulo]) => (
          <option key={valor} value={valor}>
            {rotulo}
          </option>
        ))}
      </Selecao>
    </div>
  )
}
