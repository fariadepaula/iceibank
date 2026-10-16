import json
import os
import threading
import time

import pika

from app.config import NUMERO_AGENCIAS

URL_RABBITMQ = os.getenv("RABBITMQ_URL")
EXCHANGE = "iceibank.eventos"

if not URL_RABBITMQ:
    raise SystemExit(
        "Defina a variável de ambiente RABBITMQ_URL com a URL AMQP da sua instância CloudAMQP antes de iniciar."
    )

# Conexões pika não são thread-safe: o publicador usa a sua, protegida por lock
# (as rotas síncronas do FastAPI rodam num pool de threads), e o consumidor a sua.
_lock_publicacao = threading.Lock()
_canal_publicacao = None


def _abrir_canal():
    conexao = pika.BlockingConnection(pika.URLParameters(URL_RABBITMQ))
    canal = conexao.channel()
    canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    # Declara as filas de todas as agências (idempotente): uma mensagem para uma
    # agência que nunca subiu fica retida em vez de descartada por falta de fila.
    for id_agencia in range(NUMERO_AGENCIAS):
        nome_fila = f"fila-agencia-{id_agencia}"
        canal.queue_declare(nome_fila, durable=True)
        canal.queue_bind(nome_fila, EXCHANGE, routing_key=f"agencia.{id_agencia}.creditar")
    return canal


def publicar(routing_key: str, mensagem: dict) -> None:
    global _canal_publicacao
    corpo = json.dumps(mensagem).encode()
    propriedades = pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent, content_type="application/json")
    with _lock_publicacao:
        for tentativa in range(2):
            try:
                if _canal_publicacao is None or _canal_publicacao.is_closed:
                    _canal_publicacao = _abrir_canal()
                    # Confirmação do broker: só respondemos 200 depois que o RabbitMQ aceitou a mensagem
                    _canal_publicacao.confirm_delivery()
                _canal_publicacao.basic_publish(EXCHANGE, routing_key, corpo, propriedades)
                return
            except pika.exceptions.AMQPError:
                # Conexão ociosa pode ter caído por heartbeat: reabre e tenta mais uma vez
                _canal_publicacao = None
                if tentativa == 1:
                    raise


def assinar(id_agencia: int, ao_receber_mensagem) -> None:
    nome_fila = f"fila-agencia-{id_agencia}"

    def consumir():
        while True:
            try:
                canal = _abrir_canal()

                def ao_chegar(canal, entrega, _propriedades, corpo):
                    ao_receber_mensagem(json.loads(corpo))
                    # ack manual: só sai da fila depois de processada
                    canal.basic_ack(entrega.delivery_tag)

                canal.basic_consume(nome_fila, ao_chegar)
                print(f"[mensageria] consumindo {nome_fila}")
                canal.start_consuming()
            except pika.exceptions.AMQPError as erro:
                print(f"[mensageria] conexão perdida ({erro!r}), reconectando em 5s")
                time.sleep(5)

    threading.Thread(target=consumir, name="consumidor-rabbitmq", daemon=True).start()
