# ICEIBank

Banco simplificado dividido em agências, projeto de 4 sprints.

- Sprint 1: API REST/MVC (FastAPI) + relógio lógico de Lamport + autenticação JWT + frontend (Vue.js).
- Sprint 2: transferências entre agências via RabbitMQ (publish/subscribe) + relógio vetorial no lugar do de Lamport + fila dead-letter.

Ver [`CONTEXT.md`](./CONTEXT.md) para o glossário do domínio e [`docs/adr/`](./docs/adr/) para as decisões de design registradas.

## Vídeos de apresentação

- Sprint 1: [`videos/sprint1-apresentacao.mp4`](./videos/sprint1-apresentacao.mp4) (1min53s): funcionalidades e principais decisões do projeto.
- Sprint 2: [`videos/sprint2-apresentacao.mp4`](./videos/sprint2-apresentacao.mp4) (1min53s): da transferência perdida na Sprint 1 à mensageria resiliente, fila dead-letter e relógio vetorial.

## Como rodar

RabbitMQ: crie uma instância gratuita no [CloudAMQP](https://www.cloudamqp.com/) (plano Little Lemur) e copie a AMQP URL. Para rodar localmente, use Docker:

```
docker run -d --name rabbitmq-iceibank -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Backend (repita em 3 terminais, um por agência):

```
cd agencia
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export RABBITMQ_URL="amqps://usuario:senha@host.cloudamqp.com/vhost"   # local: amqp://localhost
AGENCIA_ID=0 python -m app.main   # troque para 1 e 2 nos outros terminais
```

Todas as agências devem compartilhar o mesmo segredo JWT: exporte `ICEIBANK_JWT_SECRET` antes de subir os 3 processos.

A topologia (exchange topic `iceibank.eventos`, filas `fila-agencia-0..2` com routing key `agencia.<id>.creditar`, exchange `iceibank.mortas` e `fila-mortas`) é declarada pelas próprias agências ao subir. Se o broker ainda tiver as filas `fila-agencia-*` de uma versão anterior, sem dead-letter, apague-as uma vez no RabbitMQ Manager, já que o RabbitMQ recusa redeclarar uma fila com argumentos diferentes.

Criar uma conta exige um token de serviço (ver ADR 0002 e RESPOSTAS.md). Gere um com:

```
python mint_service_token.py
```

Linha do tempo causal (pares concorrentes e causais entre agências):

```
python mesclar_logs.py
```

Frontend:

```
cd frontend
npm install
npm run dev
```
