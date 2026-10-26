import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { CalendarRange } from 'lucide-react'
import { periodoDaUrl, type ChavePeriodo, type Periodo } from '@/compartilhado/periodo'
import type { Tanque } from '@/dominio/entidades'
import { ordenarPorUrgencia } from '@/dominio/situacao'
import { Botao } from '@/ui/Botao'
import { Campo, Selecao } from '@/ui/Campos'
import { SeletorSegmentado } from '@/ui/Navegacao'

type OpcaoPeriodo = ChavePeriodo | 'personalizado'

const OPCOES: { valor: OpcaoPeriodo; rotulo: string }[] = [
  { valor: '24h', rotulo: '24h' },
  { valor: '7d', rotulo: '7d' },
  { valor: '30d', rotulo: '30d' },
  { valor: 'personalizado', rotulo: 'Personalizado' },
]

function dataLocal(deslocamentoDias = 0): string {
  const d = new Date(Date.now() + deslocamentoDias * 86_400_000)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Tanque e período ficam na URL: o link pode ser compartilhado e o "voltar" do navegador funciona. */
export function useFiltroHistorico(tanques: Tanque[] | undefined) {
  const [parametros, setParametros] = useSearchParams()
  const periodo = periodoDaUrl(parametros)
  const idNaUrl = Number(parametros.get('tanque'))
  const lista = ordenarPorUrgencia(tanques ?? [])
  const tanque = lista.find((t) => t.id === idNaUrl) ?? lista[0]

  const atualizar = (mudancas: Record<string, string | null>) =>
    setParametros((atuais) => {
      for (const [chave, valor] of Object.entries(mudancas)) {
        if (valor === null) atuais.delete(chave)
        else atuais.set(chave, valor)
      }
      return atuais
    })

  return { periodo, tanque, lista, parametros, atualizar }
}

interface PropsSeletor {
  lista: Tanque[]
  tanque: Tanque
  periodo: Periodo
  atualizar: (mudancas: Record<string, string | null>) => void
}

export function SeletorHistorico({ lista, tanque, periodo, atualizar }: PropsSeletor) {
  const [personalizando, setPersonalizando] = useState(periodo.tipo === 'personalizado')
  const [desde, setDesde] = useState(periodo.tipo === 'personalizado' ? periodo.desde : dataLocal(-7))
  const [ate, setAte] = useState(periodo.tipo === 'personalizado' ? periodo.ate : dataLocal())
  const intervaloInvalido = !desde || !ate || desde > ate
  const opcaoAtual: OpcaoPeriodo = personalizando ? 'personalizado' : periodo.tipo === 'relativo' ? periodo.chave : 'personalizado'

  return (
    <div className="space-y-3 print:hidden">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <Selecao
          rotulo="Tanque"
          value={tanque.id}
          onChange={(e) => atualizar({ tanque: e.target.value })}
          className="sm:w-64"
        >
          {lista.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nome}
            </option>
          ))}
        </Selecao>
        <SeletorSegmentado
          rotulo="Período"
          opcoes={OPCOES}
          valor={opcaoAtual}
          aoMudar={(valor) => {
            if (valor === 'personalizado') {
              setPersonalizando(true)
              return
            }
            setPersonalizando(false)
            atualizar({ periodo: valor, desde: null, ate: null })
          }}
          className="self-start sm:ml-auto sm:self-end"
        />
      </div>
      {personalizando && (
        <form
          className="flex flex-col gap-3 rounded-xl border border-borda bg-superficie p-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault()
            if (!intervaloInvalido) atualizar({ periodo: 'personalizado', desde, ate })
          }}
        >
          <Campo rotulo="De" type="date" value={desde} max={dataLocal()} onChange={(e) => setDesde(e.target.value)} />
          <Campo
            rotulo="Até"
            type="date"
            value={ate}
            max={dataLocal()}
            onChange={(e) => setAte(e.target.value)}
            erro={desde && ate && desde > ate ? 'A data final deve ser depois da inicial.' : undefined}
          />
          <Botao type="submit" icone={CalendarRange} disabled={intervaloInvalido}>
            Aplicar
          </Botao>
        </form>
      )}
    </div>
  )
}
