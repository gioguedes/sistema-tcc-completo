import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Navigate, useLocation } from 'react-router'
import { LogIn, Waves } from 'lucide-react'
import { useTituloDocumento } from '@/compartilhado/hooks'
import { esquemaLogin, type ValoresLogin } from '@/dominio/formularios'
import { ehErroApi, mensagemDeErro } from '@/infra/api/erros'
import { Botao } from '@/ui/Botao'
import { CaixaSelecao, Campo, CampoSenha } from '@/ui/Campos'
import { Aviso } from '@/ui/Estados'
import { useAutenticacao } from './ProvedorAutenticacao'

export default function PaginaLogin() {
  useTituloDocumento('Entrar')
  const { estado, entrar } = useAutenticacao()
  const local = useLocation()
  const destino = (local.state as { destino?: string } | null)?.destino ?? '/'
  const [erroGeral, setErroGeral] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<ValoresLogin>({
    resolver: zodResolver(esquemaLogin),
    defaultValues: { email: '', senha: '', lembrar: true },
  })

  if (estado.status === 'autenticado') return <Navigate to={destino} replace />

  const enviar = handleSubmit(async (valores) => {
    setErroGeral(null)
    try {
      await entrar(valores)
    } catch (erro) {
      setErroGeral(mensagemDeErro(erro))
      if (ehErroApi(erro, 'credenciais')) setFocus('senha')
    }
  })

  const sessaoExpirada = estado.status === 'anonimo' && estado.expirada

  return (
    <main className="flex min-h-dvh items-center justify-center bg-marinho px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center text-white">
          <span className="flex size-16 items-center justify-center rounded-full bg-primaria shadow-lg">
            <Waves aria-hidden className="size-8" />
          </span>
          <h1 className="mt-4 text-2xl font-semibold">Painel Aquícola</h1>
          <p className="mt-1 text-sm text-white/80">Monitoramento inteligente da água</p>
        </div>

        <form noValidate onSubmit={enviar} className="space-y-4 rounded-2xl bg-superficie p-5 shadow-xl sm:p-6">
          {sessaoExpirada && !erroGeral && <Aviso tom="atencao">Sua sessão expirou. Entre novamente.</Aviso>}
          {erroGeral && (
            <Aviso tom="critico" urgente>
              {erroGeral}
            </Aviso>
          )}
          <Campo
            rotulo="E-mail"
            type="email"
            autoComplete="username"
            inputMode="email"
            placeholder="seu.email@exemplo.com"
            erro={errors.email?.message}
            {...register('email')}
          />
          <CampoSenha rotulo="Senha" autoComplete="current-password" erro={errors.senha?.message} {...register('senha')} />
          <CaixaSelecao rotulo="Lembrar de mim" descricao="Mantém a sessão neste aparelho." {...register('lembrar')} />
          <Botao type="submit" larguraTotal icone={LogIn} carregando={isSubmitting}>
            {isSubmitting ? 'Entrando…' : 'Entrar'}
          </Botao>
          <p className="text-center text-xs text-tinta-suave">
            Esqueceu a senha? Peça ao administrador do sistema para redefini-la.
          </p>
        </form>
      </div>
    </main>
  )
}
