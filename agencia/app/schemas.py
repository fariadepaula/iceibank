from typing import Literal

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
    # Vetor da agência no momento da leitura: o app guarda e devolve ao sincronizar
    vetorAtual: list[int] | None = None


class ValorBody(BaseModel):
    valor: float


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float
    operacaoId: str | None = None


class LoginBody(BaseModel):
    idConta: int
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SincronizarBody(BaseModel):
    tipo: Literal["DEPOSITO", "SAQUE"]
    valor: float
    vetorConhecido: list[int]
    # Se a resposta se perder e o app reenviar, a operação não é aplicada duas vezes
    operacaoId: str | None = None
