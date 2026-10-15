"""Cria um usuario do painel ou troca a senha de um que ja existe (a senha e pedida no terminal).

    python -m src.api.usuarios --email admin@exemplo.com --nome "Nome Sobrenome" --perfil admin
"""

import argparse
import getpass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.seguranca import gerar_hash_senha
from src.config import Settings
from src.db.models import Usuario
from src.db.session import criar_engine, criar_session_factory

TAMANHO_MINIMO_SENHA = 8


def definir_usuario(
    session: Session,
    email: str,
    senha: str,
    nome: str | None = None,
    perfil: str | None = None,
    telefone: str | None = None,
) -> tuple[Usuario, bool]:
    if len(senha) < TAMANHO_MINIMO_SENHA:
        raise ValueError(f"a senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres")
    email = email.strip().lower()
    usuario = session.scalar(select(Usuario).where(func.lower(Usuario.email) == email))
    if usuario is None:
        if not nome:
            raise ValueError("informe --nome para criar o usuario")
        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=gerar_hash_senha(senha),
            telefone=telefone,
            perfil=perfil or "operador",
            criado_em=datetime.now(timezone.utc),
        )
        session.add(usuario)
        session.flush()
        return usuario, True

    # usuario existente (ex.: o do seed, criado sem senha): so muda o que foi informado
    usuario.senha_hash = gerar_hash_senha(senha)
    if nome:
        usuario.nome = nome
    if perfil:
        usuario.perfil = perfil
    if telefone:
        usuario.telefone = telefone
    session.flush()
    return usuario, False


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Cria usuario do painel ou troca a senha de um existente")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nome")
    parser.add_argument("--perfil", choices=["admin", "operador"])
    parser.add_argument("--telefone", help="formato +5511987654321")
    args = parser.parse_args(argv)

    senha = getpass.getpass("Senha: ")
    if senha != getpass.getpass("Repita a senha: "):
        parser.exit(1, "as senhas nao conferem\n")

    session_factory = criar_session_factory(criar_engine(Settings()))
    with session_factory() as session:
        try:
            usuario, criado = definir_usuario(session, args.email, senha, args.nome, args.perfil, args.telefone)
        except ValueError as erro:
            parser.exit(1, f"{erro}\n")
        session.commit()
        print(f"Usuario {'criado' if criado else 'atualizado'}: {usuario.email} ({usuario.perfil})")


if __name__ == "__main__":
    main()
