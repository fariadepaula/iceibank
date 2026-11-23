"""Composição da agência: cria cada serviço uma única vez por processo e o
entrega às rotas via Depends, em vez de pendurar estado em request.app.state.
Em teste, troque qualquer um com app.dependency_overrides."""

import os
from functools import lru_cache

from app import config
from app.services.agencia import Agencia
from app.services.bully import ServicoBully


@lru_cache
def obter_agencia() -> Agencia:
    id_agencia = int(os.getenv("AGENCIA_ID", "0"))
    if not any(a["id"] == id_agencia for a in config.AGENCIAS):
        raise SystemExit(f"Agência {id_agencia} não configurada em config.py")
    return Agencia(id_agencia)


@lru_cache
def obter_bully() -> ServicoBully:
    agencia = obter_agencia()
    return ServicoBully(agencia.id, agencia.relogio, agencia.registro)
