from fastapi import APIRouter, HTTPException, Request

from app import config
from app.schemas import ContaCreate, ContaOut, ValorBody

router = APIRouter()


@router.post("/contas", response_model=ContaOut, status_code=201)
def criar_conta(corpo: ContaCreate, request: Request):
    estado = request.app.state
    if config.agencia_responsavel(corpo.id) != estado.id_agencia:
        raise HTTPException(status_code=400, detail=f"Conta {corpo.id} não pertence a esta agência.")
    if corpo.id in estado.contas:
        raise HTTPException(status_code=409, detail="Conta já existe.")

    ts = estado.relogio.evento_local()
    estado.contas[corpo.id] = {"id": corpo.id, "nomeAluno": corpo.nomeAluno, "saldo": corpo.saldoInicial}
    estado.registro.registrar(
        "CRIAR_CONTA", ts, {"id": corpo.id, "nomeAluno": corpo.nomeAluno, "saldoInicial": corpo.saldoInicial}
    )
    return estado.contas[corpo.id]


@router.get("/contas/{id}", response_model=ContaOut)
def consultar_saldo(id: int, request: Request):
    conta = request.app.state.contas.get(id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
    return conta


@router.post("/contas/{id}/depositar", response_model=ContaOut)
def depositar(id: int, corpo: ValorBody, request: Request):
    estado = request.app.state
    conta = estado.contas.get(id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")

    ts = estado.relogio.evento_local()
    conta["saldo"] += corpo.valor
    estado.registro.registrar("DEPOSITO", ts, {"id": id, "valor": corpo.valor, "novoSaldo": conta["saldo"]})
    return conta


@router.post("/contas/{id}/sacar", response_model=ContaOut)
def sacar(id: int, corpo: ValorBody, request: Request):
    estado = request.app.state
    conta = estado.contas.get(id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
    if conta["saldo"] < corpo.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    ts = estado.relogio.evento_local()
    conta["saldo"] -= corpo.valor
    estado.registro.registrar("SAQUE", ts, {"id": id, "valor": corpo.valor, "novoSaldo": conta["saldo"]})
    return conta
