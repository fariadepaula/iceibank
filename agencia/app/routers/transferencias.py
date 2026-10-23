import pika
from fastapi import APIRouter, Depends, HTTPException, Request

from app import config
from app.schemas import TransferenciaBody
from app.services.auth import principal_atual
from app.services.mensageria import publicar

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

    # Caso entre agências: em vez de chamar a outra agência via REST (Sprint 1),
    # publica um evento na exchange. A agência de destino consome quando puder -
    # se estiver fora do ar agora, a mensagem fica retida na fila durável.
    ts_envio = estado.relogio.ao_enviar()
    try:
        publicar(
            f"agencia.{agencia_destino}.creditar",
            {
                "idConta": corpo.idDestino,
                "valor": corpo.valor,
                "vetorEnvio": ts_envio,
                "origemAgencia": estado.id_agencia,
                "idOrigem": corpo.idOrigem,
                "operacaoId": corpo.operacaoId,
            },
        )
    except pika.exceptions.AMQPError as erro:
        # Nada saiu deste processo, então desfazer o débito aqui é seguro
        conta_origem["saldo"] += corpo.valor
        estado.registro.registrar(
            "TRANSFERENCIA_FALHOU",
            estado.relogio.evento_local(),
            {"idOrigem": corpo.idOrigem, "idDestino": corpo.idDestino, "valor": corpo.valor, "erro": repr(erro)},
        )
        raise HTTPException(status_code=503, detail="Broker de mensagens indisponível. Débito desfeito, tente novamente.")

    # 200 aqui significa "publicada", não "creditada": o crédito é assíncrono
    resultado = {"mensagem": "Transferência publicada para a agência de destino (entrega assíncrona)."}
    if corpo.operacaoId:
        estado.operacoes_vistas[corpo.operacaoId] = resultado
    return resultado


def aplicar_credito_remoto(estado, mensagem: dict) -> bool:
    """Consumidor da fila desta agência. Devolve False se o crédito não puder ser
    aplicado - a mensagem vai então para a fila dead-letter."""
    operacao_id = mensagem.get("operacaoId")
    # Entrega é "pelo menos uma vez": uma mensagem repetida não credita duas vezes
    if operacao_id and operacao_id in estado.operacoes_vistas:
        return True

    # Ao RECEBER uma mensagem de outra agência, o vetor local é mesclado
    # posição a posição com o recebido - é a regra 3 do algoritmo.
    ts = estado.relogio.ao_receber(mensagem["vetorEnvio"])
    detalhes = {"idConta": mensagem["idConta"], "valor": mensagem["valor"], "origemAgencia": mensagem["origemAgencia"]}

    conta = estado.contas.get(mensagem["idConta"])
    if not conta:
        estado.registro.registrar("CREDITO_REMOTO_FALHOU", ts, {**detalhes, "motivo": "conta não encontrada"})
        return False

    conta["saldo"] += mensagem["valor"]
    estado.registro.registrar("TRANSFERENCIA_CREDITO_REMOTO", ts, detalhes)
    if operacao_id:
        estado.operacoes_vistas[operacao_id] = {"mensagem": "Crédito remoto aplicado."}
    return True
