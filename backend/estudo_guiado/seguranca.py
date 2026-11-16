"""Primitivas de segurança para autenticação: hash de senha (scrypt), tokens de sessão e validações."""
import base64
import hashlib
import hmac
import re
import secrets

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
TAMANHO_MINIMO_SENHA = 8
PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode()


def hash_senha(senha: str) -> str:
    """Formato: scrypt$N$r$p$salt$hash (salt aleatório por usuário)."""
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(senha.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(h)}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    try:
        _, n, r, p, salt, esperado = armazenado.split("$")
        h = hashlib.scrypt(senha.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(h, base64.b64decode(esperado))
    except (ValueError, TypeError):
        return False


def novo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """O banco guarda só o hash do token: vazamento do arquivo não permite reaproveitar sessões."""
    return hashlib.sha256(token.encode()).hexdigest()


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def email_valido(email: str) -> bool:
    return bool(PADRAO_EMAIL.match(email)) and len(email) <= 254


def validar_senha(senha: str) -> str | None:
    """Devolve a mensagem de erro, ou None se a senha é aceitável."""
    if len(senha) < TAMANHO_MINIMO_SENHA:
        return f"A senha precisa ter ao menos {TAMANHO_MINIMO_SENHA} caracteres."
    if not (re.search(r"[A-Za-z]", senha) and re.search(r"\d", senha)):
        return "A senha precisa combinar letras e números."
    return None
