from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencias import obter_bully
from app.services.bully import ServicoBully

router = APIRouter(prefix="/bully")


class EleicaoBody(BaseModel):
    origemId: int
    vetorEnvio: list[int]


class CoordenadorBody(BaseModel):
    liderId: int
    vetorEnvio: list[int]


@router.post("/eleicao")
def eleicao(corpo: EleicaoBody, bully: ServicoBully = Depends(obter_bully)):
    bully.receber_eleicao(corpo.origemId, corpo.vetorEnvio)
    return {"ok": True}


@router.post("/coordenador")
def coordenador(corpo: CoordenadorBody, bully: ServicoBully = Depends(obter_bully)):
    bully.receber_coordenador(corpo.liderId, corpo.vetorEnvio)
    return {"ok": True}


@router.get("/lider")
def lider(bully: ServicoBully = Depends(obter_bully)):
    return {"idAgencia": bully.id_agencia, "liderAtual": bully.obter_lider_atual()}
