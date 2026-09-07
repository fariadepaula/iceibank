import requests
from fastapi import APIRouter, Depends, HTTPException, Request

from app import config
from app.schemas import CreditarRemotoBody, TransferenciaBody
from app.services.auth import criar_token_servico, exigir_servico, principal_atual

router = APIRouter()


@router.post("/transferencias")
def transferir(corpo: TransferenciaBody, request: Request, principal: dict = Depends(principal_atual)):
    if principal.get("tipo") != "conta" or principal.get("sub") != str(corpo.idOrigem):
        raise HTTPException(status_code=403, detail="Este token não autoriza transferir desta conta.")

    estado = request.app.state

    # Idempotência: se este operacaoId já foi processado, devolve o mesmo
    # resultado sem reaplicar o débito/crédito (funcionalidade adicional).
    if corpo.operacaoId and corpo.operacaoId in estado.operacoes_vistas:
        return estado.operacoes_vistas[corpo.operacaoId]

    conta_origem = estado.contas.get(corpo.idOrigem)
    if not conta_origem:
        raise HTTPException(status_code=404, detail="Conta de origem não encontrada nesta agência.")
    if conta_origem["saldo"] < corpo.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    agencia_destino = config.agencia_responsavel(corpo.idDestino)

    # O débito é sempre local, pois esta agência é a dona da conta de origem
    ts_debito = estado.relogio.evento_local()
    conta_origem["saldo"] -= corpo.valor
    estado.registro.registrar(
        "TRANSFERENCIA_DEBITO", ts_debito, {"idOrigem": corpo.idOrigem, "idDestino": corpo.idDestino, "valor": corpo.valor}
    )

    if agencia_destino == estado.id_agencia:
        conta_destino = estado.contas.get(corpo.idDestino)
        if not conta_destino:
            conta_origem["saldo"] += corpo.valor
            raise HTTPException(status_code=404, detail="Conta de destino não encontrada.")
        ts_credito = estado.relogio.evento_local()
        conta_destino["saldo"] += corpo.valor
        estado.registro.registrar(
            "TRANSFERENCIA_CREDITO", ts_credito, {"idOrigem": corpo.idOrigem, "idDestino": corpo.idDestino, "valor": corpo.valor}
        )
        resultado = {"mensagem": "Transferência concluída (mesma agência)."}
        if corpo.operacaoId:
            estado.operacoes_vistas[corpo.operacaoId] = resultado
        return resultado

    # Caso entre agências: chama a agência de destino diretamente via REST,
    # autenticada como chamada de serviço (não com o token do usuário - ADR 0002)
    ts_envio = estado.relogio.ao_enviar()
    url_destino = next(a["url"] for a in config.AGENCIAS if a["id"] == agencia_destino)

    try:
        resposta = requests.post(
            f"{url_destino}/contas/{corpo.idDestino}/creditar-remoto",
            json={
                "valor": corpo.valor,
                "timestampLamport": ts_envio,
                "origemAgencia": estado.id_agencia,
                "operacaoId": corpo.operacaoId,
            },
            headers={"Authorization": f"Bearer {criar_token_servico()}"},
            timeout=5,
        )
        resposta.raise_for_status()
        resultado = {"mensagem": "Transferência concluída (entre agências)."}
        if corpo.operacaoId:
            estado.operacoes_vistas[corpo.operacaoId] = resultado
        return resultado
    except requests.RequestException as erro:
        # LIMITAÇÃO CONHECIDA: se esta chamada falhar, o débito já aplicado acima
        # NÃO é revertido - o dinheiro "desaparece" temporariamente. Resolver isso
        # de forma correta é o assunto do Sprint 4 (2PC/Saga). Por enquanto, só
        # registramos a inconsistência no log.
        estado.registro.registrar(
            "TRANSFERENCIA_FALHOU",
            estado.relogio.evento_local(),
            {"idOrigem": corpo.idOrigem, "idDestino": corpo.idDestino, "valor": corpo.valor, "erro": str(erro)},
        )
        raise HTTPException(
            status_code=502,
            detail="Falha ao contatar agência de destino. Débito já aplicado - inconsistência conhecida (ver Sprint 4).",
        )


@router.post("/contas/{id}/creditar-remoto")
def creditar_remoto(id: int, corpo: CreditarRemotoBody, request: Request, _servico: dict = Depends(exigir_servico)):
    estado = request.app.state

    if corpo.operacaoId and corpo.operacaoId in estado.operacoes_vistas:
        return estado.operacoes_vistas[corpo.operacaoId]

    # Ao RECEBER uma mensagem de outra agência, o relógio de Lamport é
    # atualizado com base no timestamp recebido - é a regra 3 do algoritmo.
    ts = estado.relogio.ao_receber(corpo.timestampLamport)

    conta = estado.contas.get(id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")

    conta["saldo"] += corpo.valor
    estado.registro.registrar(
        "TRANSFERENCIA_CREDITO_REMOTO", ts, {"idConta": id, "valor": corpo.valor, "origemAgencia": corpo.origemAgencia}
    )
    resultado = {"mensagem": "Crédito remoto aplicado.", "saldoAtual": conta["saldo"]}
    if corpo.operacaoId:
        estado.operacoes_vistas[corpo.operacaoId] = resultado
    return resultado
