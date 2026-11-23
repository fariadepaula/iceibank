"""Transparência de localização: qualquer agência aceita a requisição e, se a
conta for de outra partição, repassa para a agência dona e devolve a resposta
dela. O cliente não precisa saber que id_conta % 3 existe."""

import requests
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app import config

CABECALHO_ENCAMINHADO = "X-ICEIBank-Encaminhado"
TIMEOUT_S = 3


def encaminhar(request: Request, id_conta: int, corpo: dict | None = None) -> JSONResponse:
    if request.headers.get(CABECALHO_ENCAMINHADO):
        # Se já veio encaminhada e mesmo assim não é daqui, as agências estão com
        # configurações diferentes. Falhar evita repassar a requisição em círculo.
        raise HTTPException(status_code=500, detail="Requisição encaminhada para a agência errada.")

    destino = config.AGENCIAS[config.agencia_responsavel(id_conta)]
    cabecalhos = {CABECALHO_ENCAMINHADO: "1"}
    if "authorization" in request.headers:
        cabecalhos["Authorization"] = request.headers["authorization"]

    try:
        resposta = requests.request(
            request.method, f"{destino['url']}{request.url.path}", json=corpo, headers=cabecalhos, timeout=TIMEOUT_S
        )
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail=f"Agência {destino['id']}, dona da conta {id_conta}, está indisponível.")

    try:
        conteudo = resposta.json()
    except ValueError:
        conteudo = {"detail": resposta.text}
    return JSONResponse(status_code=resposta.status_code, content=conteudo)
