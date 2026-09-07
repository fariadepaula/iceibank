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
