import { useState, type MouseEvent } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Accessibility, LogOut, Save, X } from 'lucide-react'
import { useTituloDocumento } from '@/compartilhado/hooks'
import { esquemaConta, formatarTelefone, normalizarTelefone, type ValoresConta } from '@/dominio/formularios'
import { ROTULO_PERFIL } from '@/dominio/rotulos'
import { atualizarConta } from '@/infra/api/autenticacao'
import type { Tema } from '@/infra/armazenamento/preferencias'
import { Botao } from '@/ui/Botao'
import { Alternador, CampoBusca, Campo } from '@/ui/Campos'
import { CabecalhoCartao, Cartao } from '@/ui/Cartao'
import { Aviso } from '@/ui/Estados'
import { SeletorSegmentado } from '@/ui/Navegacao'
import { useToast } from '@/ui/Toast'
import { CartaoAplicativo } from '../../componentes/Aplicativo'
import { aplicarErrosDaApi } from '../../componentes/formularios'
import { usePreferencias } from '../../preferencias'
import { aplicarTema, trocarTemaComTransicao } from '../../tema'
import { useAutenticacao, useUsuario } from '../autenticacao/ProvedorAutenticacao'

// Textos do glossário vindos do Figma ("06 · Modo avançado / Glossário").
const GLOSSARIO = [
  { termo: 'pH', definicao: 'Se a água está mais ácida ou mais alcalina.' },
  { termo: 'Turbidez / NTU', definicao: 'Medida técnica de partículas na água.' },
  { termo: 'Aeração', definicao: 'Equipamento que adiciona oxigênio na água.' },
  {
    termo: 'OD (Oxigênio dissolvido)',
    definicao: 'É a quantidade de oxigênio na água, essencial para a vida dos peixes. Abaixo de 3 mg/L, o risco é alto.',
  },
]

const OPCOES_TEMA: { valor: Tema; rotulo: string }[] = [
  { valor: 'automatico', rotulo: 'Automático' },
  { valor: 'claro', rotulo: 'Claro' },
  { valor: 'escuro', rotulo: 'Escuro' },
]

const normalizar = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

function FormularioConta() {
  const usuario = useUsuario()
  const { atualizarUsuario } = useAutenticacao()
  const { mostrar } = useToast()
  const [erroGeral, setErroGeral] = useState<string | null>(null)
  const salvar = useMutation({ mutationFn: atualizarConta })
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ValoresConta>({
    resolver: zodResolver(esquemaConta),
    defaultValues: { nome: usuario.nome, telefone: formatarTelefone(usuario.telefone) },
  })

  const enviar = handleSubmit(async (valores) => {
    setErroGeral(null)
    try {
      const atualizado = await salvar.mutateAsync({
        nome: valores.nome,
        telefone: valores.telefone ? normalizarTelefone(valores.telefone) : null,
      })
      atualizarUsuario(atualizado)
      reset({ nome: atualizado.nome, telefone: formatarTelefone(atualizado.telefone) })
      mostrar('Dados da conta atualizados.')
    } catch (erro) {
      setErroGeral(aplicarErrosDaApi(erro, setError))
    }
  })

  return (
    <form noValidate onSubmit={enviar} className="space-y-4">
      {erroGeral && (
        <Aviso tom="critico" urgente>
          {erroGeral}
        </Aviso>
      )}
      {!usuario.telefone && (
        <Aviso tom="atencao" titulo="Cadastre seu WhatsApp">
          Sem telefone, você não recebe os alertas críticos fora do painel.
        </Aviso>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Campo rotulo="Nome" obrigatorio autoComplete="name" erro={errors.nome?.message} {...register('nome')} />
        <Campo
          rotulo="WhatsApp"
          type="tel"
          autoComplete="tel-national"
          inputMode="tel"
          placeholder="(11) 98765-4321"
          dica="Usado para receber os alertas críticos."
          erro={errors.telefone?.message}
          {...register('telefone')}
        />
        <Campo rotulo="E-mail" value={usuario.email} readOnly disabled dica="Para trocar o e-mail, fale com o administrador." />
        <Campo rotulo="Perfil" value={ROTULO_PERFIL[usuario.perfil]} readOnly disabled />
      </div>
      <div className="flex justify-end">
        <Botao type="submit" icone={Save} carregando={isSubmitting} disabled={!isDirty}>
          Salvar
        </Botao>
      </div>
    </form>
  )
}

export default function PaginaConfiguracoes() {
  useTituloDocumento('Configurações')
  const { sair } = useAutenticacao()
  const { modoAvancado, linguagemSimples, explicacaoOdDispensada, tema, alterar } = usePreferencias()
  const [busca, setBusca] = useState('')
  const trocarTema = (novo: Tema, evento: MouseEvent<HTMLButtonElement>) => {
    if (novo === tema) return
    // o círculo parte do botão tocado (também quando a troca vem do teclado)
    const botao = evento.currentTarget.getBoundingClientRect()
    trocarTemaComTransicao(
      () => {
        alterar({ tema: novo })
        aplicarTema(novo)
      },
      { x: botao.left + botao.width / 2, y: botao.top + botao.height / 2 },
    )
  }
  const termos = GLOSSARIO.filter((g) => normalizar(`${g.termo} ${g.definicao}`).includes(normalizar(busca)))

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Configurações</h1>
        <p className="mt-1 text-tinta-suave">Sua conta, preferências de exibição e glossário.</p>
      </header>

      <Cartao aria-labelledby="titulo-conta">
        <CabecalhoCartao id="titulo-conta" titulo="Minha conta" />
        <FormularioConta />
      </Cartao>

      <Cartao aria-labelledby="titulo-preferencias" className="space-y-5">
        <CabecalhoCartao id="titulo-preferencias" titulo="Preferências" className="mb-0" />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Tema</p>
            <p className="text-xs text-tinta-suave">Automático segue o tema do aparelho. O claro é o mais legível sob sol.</p>
          </div>
          <SeletorSegmentado rotulo="Tema" opcoes={OPCOES_TEMA} valor={tema} aoMudar={trocarTema} />
        </div>
        <Alternador
          rotulo="Modo avançado"
          descricao="Mostra valores técnicos, faixas ideais detalhadas e a confiança das previsões."
          ligado={modoAvancado}
          aoAlternar={(v) => alterar({ modoAvancado: v })}
        />
        <Alternador
          rotulo="Linguagem simples"
          descricao="Troca termos técnicos por explicações do dia a dia."
          ligado={linguagemSimples}
          aoAlternar={(v) => alterar({ linguagemSimples: v })}
        />
        <p className="text-xs text-tinta-suave">As preferências ficam salvas neste aparelho.</p>
      </Cartao>

      <CartaoAplicativo />

      {!explicacaoOdDispensada && (
        <section aria-labelledby="titulo-od" className="relative rounded-xl border border-primaria/20 bg-primaria-fundo p-4 pr-14">
          <h2 id="titulo-od" className="font-semibold">
            OD (Oxigênio dissolvido)
          </h2>
          <p className="mt-1 text-sm text-tinta-suave">
            É a quantidade de oxigênio na água, essencial para a vida dos peixes. Abaixo de 3 mg/L, o risco é alto. No
            painel, o valor é estimado pelo modelo de Machine Learning.
          </p>
          <button
            type="button"
            aria-label="Dispensar explicação"
            onClick={() => alterar({ explicacaoOdDispensada: true })}
            className="absolute top-2 right-2 flex size-11 items-center justify-center rounded-lg text-tinta-suave hover:bg-superficie/60"
          >
            <X aria-hidden className="size-5" />
          </button>
        </section>
      )}

      <Cartao aria-labelledby="titulo-glossario">
        <CabecalhoCartao id="titulo-glossario" titulo="Glossário" />
        <CampoBusca rotulo="Buscar no glossário" placeholder="Buscar termo…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        <dl className="mt-3 divide-y divide-borda">
          {termos.map((g) => (
            <div key={g.termo} className="py-3">
              <dt className="font-semibold">{g.termo}</dt>
              <dd className="text-sm text-tinta-suave">{g.definicao}</dd>
            </div>
          ))}
        </dl>
        {termos.length === 0 && <p className="mt-3 text-sm text-tinta-suave">Nenhum termo encontrado.</p>}
      </Cartao>

      <p className="flex items-start gap-2 rounded-xl bg-neutro-fundo p-3 text-xs text-tinta-suave">
        <Accessibility aria-hidden className="mt-px size-4 shrink-0" />
        Contraste, textos grandes e navegação por teclado seguem as diretrizes de acessibilidade (WCAG 2.2).
      </p>

      <Botao variante="secundario" icone={LogOut} larguraTotal onClick={() => void sair()} className="text-critico sm:w-auto">
        Sair da conta
      </Botao>
    </div>
  )
}
