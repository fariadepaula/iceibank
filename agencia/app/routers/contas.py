from fastapi import APIRouter, Depends, Request

from app.dependencias import obter_agencia
from app.schemas import ContaCreate, ContaOut, ValorBody
from app.services.agencia import Agencia
from app.services.auth import exigir_dono_da_conta, exigir_servico
from app.services.encaminhamento import encaminhar

router = APIRouter()


@router.post("/contas", response_model=ContaOut, status_code=201)
def criar_conta(
    corpo: ContaCreate,
    request: Request,
    agencia: Agencia = Depends(obter_agencia),
    _servico: dict = Depends(exigir_servico),
):
    if not agencia.e_dona(corpo.id):
        return encaminhar(request, corpo.id, corpo.model_dump())
    return agencia.criar_conta(corpo.id, corpo.nomeAluno, corpo.senha, corpo.saldoInicial)


@router.get("/contas/{id}", response_model=ContaOut)
def consultar_saldo(
    id: int,
    request: Request,
    agencia: Agencia = Depends(obter_agencia),
    _principal: dict = Depends(exigir_dono_da_conta),
):
    if not agencia.e_dona(id):
        return encaminhar(request, id)
    return agencia.consultar(id)


@router.post("/contas/{id}/depositar", response_model=ContaOut)
def depositar(
    id: int,
    corpo: ValorBody,
    request: Request,
    agencia: Agencia = Depends(obter_agencia),
    _principal: dict = Depends(exigir_dono_da_conta),
):
    if not agencia.e_dona(id):
        return encaminhar(request, id, corpo.model_dump())
    return agencia.depositar(id, corpo.valor)


@router.post("/contas/{id}/sacar", response_model=ContaOut)
def sacar(
    id: int,
    corpo: ValorBody,
    request: Request,
    agencia: Agencia = Depends(obter_agencia),
    _principal: dict = Depends(exigir_dono_da_conta),
):
    if not agencia.e_dona(id):
        return encaminhar(request, id, corpo.model_dump())
    return agencia.sacar(id, corpo.valor)
