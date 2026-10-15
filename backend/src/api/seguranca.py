import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

# scrypt da biblioteca padrao: guarda a senha sem dependencia nova
_N, _R, _P = 2**14, 8, 1
ALGORITMO_JWT = "HS256"
ACESSO = "acesso"
RENOVACAO = "renovacao"


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    chave = hashlib.scrypt(senha.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${sal.hex()}${chave.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        algoritmo, n, r, p, sal, esperado = senha_hash.split("$")
        if algoritmo != "scrypt":
            return False
        chave = hashlib.scrypt(
            senha.encode(), salt=bytes.fromhex(sal), n=int(n), r=int(r), p=int(p), dklen=len(esperado) // 2
        )
    except ValueError:
        # hash em outro formato (ex.: o texto fixo do seed): usuario ainda sem senha definida
        return False
    return hmac.compare_digest(chave.hex(), esperado)


# usado quando o e-mail nao existe, para o login levar o mesmo tempo nos dois casos
HASH_FICTICIO = gerar_hash_senha(secrets.token_urlsafe(16))


def emitir_token(
    id_usuario: int, tipo: str, validade: timedelta, segredo: str, **extras
) -> tuple[str, datetime]:
    agora = datetime.now(timezone.utc)
    expira_em = agora + validade
    dados = {"sub": str(id_usuario), "tipo": tipo, "iat": agora, "exp": expira_em, **extras}
    return jwt.encode(dados, segredo, algorithm=ALGORITMO_JWT), expira_em


def ler_token(token: str, tipo: str, segredo: str) -> dict | None:
    try:
        dados = jwt.decode(
            token, segredo, algorithms=[ALGORITMO_JWT], options={"require": ["sub", "exp", "tipo"]}
        )
    except jwt.InvalidTokenError:
        return None
    # token de renovacao nao serve como token de acesso, e vice-versa
    return dados if dados["tipo"] == tipo else None
