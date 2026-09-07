import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Todas as 3 agências precisam compartilhar o mesmo valor (exporte antes de
# subir os 3 processos) - ver ADR 0002.
SECRET_KEY = os.getenv("ICEIBANK_JWT_SECRET", "chave-de-desenvolvimento-trocar-em-producao")
ALGORITHM = "HS256"
EXPIRACAO_CONTA = timedelta(minutes=20)
EXPIRACAO_SERVICO = timedelta(hours=24)

_bearer = HTTPBearer(auto_error=False)


def hash_senha(senha: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 100_000)
    return f"{salt.hex()}:{derivado.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    salt_hex, derivado_hex = hash_armazenado.split(":")
    esperado = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt_hex), 100_000)
    return hmac.compare_digest(esperado.hex(), derivado_hex)


def criar_token_conta(id_conta: int) -> str:
    payload = {"sub": str(id_conta), "tipo": "conta", "exp": datetime.now(timezone.utc) + EXPIRACAO_CONTA}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def criar_token_servico() -> str:
    payload = {"tipo": "servico", "exp": datetime.now(timezone.utc) + EXPIRACAO_SERVICO}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decodificar(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token ausente, inválido ou expirado.")


def principal_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if credenciais is None:
        raise HTTPException(status_code=401, detail="Token ausente, inválido ou expirado.")
    return _decodificar(credenciais.credentials)


def exigir_dono_da_conta(id: int, principal: dict = Depends(principal_atual)) -> dict:
    if principal.get("tipo") != "conta" or principal.get("sub") != str(id):
        raise HTTPException(status_code=403, detail="Este token não autoriza operar nesta conta.")
    return principal


def exigir_servico(principal: dict = Depends(principal_atual)) -> dict:
    if principal.get("tipo") != "servico":
        raise HTTPException(status_code=403, detail="Rota exclusiva para chamadas de serviço (entre agências).")
    return principal


def _selfcheck():
    h = hash_senha("segredo123")
    assert verificar_senha("segredo123", h)
    assert not verificar_senha("errada", h)

    token = criar_token_conta(7)
    payload = _decodificar(token)
    assert payload["sub"] == "7" and payload["tipo"] == "conta"

    servico = criar_token_servico()
    assert _decodificar(servico)["tipo"] == "servico"

    print("auth: ok")


if __name__ == "__main__":
    _selfcheck()
