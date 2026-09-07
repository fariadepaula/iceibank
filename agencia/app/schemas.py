from pydantic import BaseModel


class ContaCreate(BaseModel):
    id: int
    nomeAluno: str
    senha: str
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
    operacaoId: str | None = None


class CreditarRemotoBody(BaseModel):
    valor: float
    timestampLamport: int
    origemAgencia: int
    operacaoId: str | None = None


class LoginBody(BaseModel):
    idConta: int
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
