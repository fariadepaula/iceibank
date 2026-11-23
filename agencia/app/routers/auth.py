from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencias import obter_agencia
from app.schemas import LoginBody, TokenOut
from app.services.agencia import Agencia
from app.services.auth import criar_token_conta
from app.services.encaminhamento import encaminhar

router = APIRouter()


@router.post("/auth/login", response_model=TokenOut)
def login(corpo: LoginBody, request: Request, agencia: Agencia = Depends(obter_agencia)):
    # Qualquer agência serve de porta de entrada: se a conta é de outra, repassa
    if not agencia.e_dona(corpo.idConta):
        return encaminhar(request, corpo.idConta, corpo.model_dump())
    if not agencia.autenticar(corpo.idConta, corpo.senha):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")
    return TokenOut(access_token=criar_token_conta(corpo.idConta))
