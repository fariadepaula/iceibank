from fastapi import APIRouter, HTTPException, Request

from app.schemas import LoginBody, TokenOut
from app.services.auth import criar_token_conta, verificar_senha

router = APIRouter()


@router.post("/auth/login", response_model=TokenOut)
def login(corpo: LoginBody, request: Request):
    conta = request.app.state.contas.get(corpo.idConta)
    if not conta or not verificar_senha(corpo.senha, conta["senha_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")
    return TokenOut(access_token=criar_token_conta(corpo.idConta))
