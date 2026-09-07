from pydantic import BaseModel


class ContaCreate(BaseModel):
    id: int
    nomeAluno: str
    saldoInicial: float = 0


class ContaOut(BaseModel):
    id: int
    nomeAluno: str
    saldo: float


class ValorBody(BaseModel):
    valor: float


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float


class CreditarRemotoBody(BaseModel):
    valor: float
    timestampLamport: int
    origemAgencia: int
