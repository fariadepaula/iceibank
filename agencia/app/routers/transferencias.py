from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencias import obter_agencia
from app.schemas import TransferenciaBody
from app.services.agencia import Agencia
from app.services.auth import principal_atual
from app.services.encaminhamento import encaminhar

router = APIRouter()


@router.post("/transferencias")
def transferir(
    corpo: TransferenciaBody,
    request: Request,
    agencia: Agencia = Depends(obter_agencia),
    principal: dict = Depends(principal_atual),
):
    if principal.get("tipo") != "conta" or principal.get("sub") != str(corpo.idOrigem):
        raise HTTPException(status_code=403, detail="Este token não autoriza transferir desta conta.")
    # O débito precisa acontecer na agência dona da conta de origem
    if not agencia.e_dona(corpo.idOrigem):
        return encaminhar(request, corpo.idOrigem, corpo.model_dump())
    return agencia.transferir(corpo.idOrigem, corpo.idDestino, corpo.valor, corpo.operacaoId)
