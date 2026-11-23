# ICEIBank

Banco simplificado dividido em agências, projeto de 4 sprints.

- Sprint 1: API REST/MVC (FastAPI) + relógio lógico de Lamport + autenticação JWT + frontend (Vue.js).
- Sprint 2: transferências entre agências via RabbitMQ (publish/subscribe) + relógio vetorial no lugar do de Lamport + fila dead-letter.
- Sprint 3: eleição de líder (Bully) com heartbeat, sincronização offline-first com detecção de conflito pelo relógio vetorial, app Flutter (`app_mobile/`) com painel de liderança e modo offline.

Ver [`CONTEXT.md`](./CONTEXT.md) para o glossário do domínio e [`docs/adr/`](./docs/adr/) para as decisões de design registradas.

## Vídeos de apresentação

- Sprint 1: [`videos/sprint1-apresentacao.mp4`](./videos/sprint1-apresentacao.mp4) (1min53s): funcionalidades e principais decisões do projeto.
- Sprint 2: [`videos/sprint2-apresentacao.mp4`](./videos/sprint2-apresentacao.mp4) (1min53s): da transferência perdida na Sprint 1 à mensageria resiliente, fila dead-letter e relógio vetorial.

## Arquitetura

```
 frontend Vue (5173)      app Flutter
          \                  /
           HTTP + JWT (qualquer agência)
          /         |          \
  Agência 0     Agência 1     Agência 2      FastAPI, portas 4071-4073
  contas id%3=0 contas id%3=1 contas id%3=2
       \            |            /
        RabbitMQ (exchange iceibank.eventos, fila por agência, fila-mortas)
```

- Cada agência é um processo FastAPI que guarda em memória só as contas da sua partição (`id % 3`). Não há banco compartilhado.
- Qualquer agência aceita qualquer requisição. Se a conta é de outra partição, a agência repassa a requisição para a dona.
- Transferência entre agências: a origem debita e publica uma mensagem no RabbitMQ, e a destino credita ao consumir. Mensagens que falham vão para a `fila-mortas`. O `operacaoId` impede crédito ou débito duplicado.
- Cada agência mantém um relógio vetorial e grava os eventos em `agencia/data/agencia-<id>.jsonl`. O `mesclar_logs.py` monta a linha do tempo causal a partir desses arquivos.
- As agências elegem uma líder pelo algoritmo Bully (vence o maior ID ativo) e checam a líder a cada 3 s. Se ela não responde, uma nova eleição começa.
- O app Flutter guarda o saldo e uma fila de depósitos e saques feitos sem conexão. Ao reconectar, ele envia cada operação com o vetor que conhecia, e a agência recusa com 409 se o vetor mudou desde então.

## Como rodar

Requisitos: Python 3.12+, Docker, Node 20+ e, para o app, Flutter 3.50.1 (`mise install` na raiz instala a versão fixada no `mise.toml`).

1. RabbitMQ local (ou uma instância gratuita no [CloudAMQP](https://www.cloudamqp.com/), plano Little Lemur):

   ```
   docker run -d --name rabbitmq-iceibank -p 5672:5672 -p 15672:15672 rabbitmq:3-management
   ```

2. Ambiente do backend, uma vez:

   ```
   cd agencia
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. As 3 agências, cada uma num terminal. As três precisam do mesmo segredo JWT:

   ```
   export RABBITMQ_URL="amqp://localhost"
   export ICEIBANK_JWT_SECRET="troque-por-uma-chave-com-32-bytes-ou-mais"
   AGENCIA_ID=0 python -m app.main   # 1 e 2 nos outros terminais
   ```

   As agências declaram a topologia do RabbitMQ ao subir. Se o broker tiver filas `fila-agencia-*` de uma versão antiga, sem dead-letter, apague-as uma vez no RabbitMQ Manager (http://localhost:15672, guest/guest).

4. Frontend web (http://localhost:5173):

   ```
   cd frontend && npm install && npm run dev
   ```

5. App Flutter:

   ```
   cd app_mobile && flutter pub get
   flutter run -d chrome                                   # ou -d linux
   flutter run --dart-define=AGENCIA_HOST=10.0.2.2         # emulador Android
   ```

## Cenários de teste

Os comandos abaixo rodam num terminal com a venv ativa, dentro de `agencia/` e com o mesmo `ICEIBANK_JWT_SECRET` das agências. Primeiro, crie duas contas em partições diferentes e faça login:

```
SVC=$(python mint_service_token.py)
for id in 7 8; do
  curl -s -X POST localhost:4071/contas -H "Authorization: Bearer $SVC" -H 'Content-Type: application/json' \
    -d "{\"id\":$id,\"nomeAluno\":\"Aluno $id\",\"senha\":\"demo123\",\"saldoInicial\":500}"
done
login() { curl -s -X POST localhost:4071/auth/login -H 'Content-Type: application/json' \
  -d "{\"idConta\":$1,\"senha\":\"demo123\"}" | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'; }
T7=$(login 7); T8=$(login 8)
```

A conta 7 fica na agência 1 (7 % 3) e a 8 na agência 2, mesmo com tudo enviado para a agência 0.

### Contas e autenticação

| Cenário | Comando | Comportamento esperado |
|---|---|---|
| Consultar a própria conta por outra agência | `curl -s localhost:4071/contas/8 -H "Authorization: Bearer $T8"` | 200 com o saldo. A agência 0 repassa para a 2 |
| Consultar conta de outra pessoa | `curl -s localhost:4071/contas/7 -H "Authorization: Bearer $T8"` | 403 |
| Sem token | `curl -s localhost:4071/contas/8` | 401 |
| Senha errada | login com `"senha":"x"` | 401, "Credenciais inválidas." |
| Criar conta sem token de serviço | o `POST /contas` acima sem o header | 401 |
| Saque maior que o saldo | `curl -s -X POST localhost:4071/contas/8/sacar -H "Authorization: Bearer $T8" -H 'Content-Type: application/json' -d '{"valor":9999}'` | 400, "Saldo insuficiente.", saldo inalterado |

### Transferências e mensageria

| Cenário | Comando | Comportamento esperado |
|---|---|---|
| Transferência entre agências | `curl -s -X POST localhost:4071/transferencias -H "Authorization: Bearer $T8" -H 'Content-Type: application/json' -d '{"idOrigem":8,"idDestino":7,"valor":100,"operacaoId":"t1"}'` | 200 "publicada". A conta 8 cai para 400 na hora e a 7 sobe para 600 logo depois, ao consumir a fila |
| Repetir a mesma transferência | o mesmo comando, com o mesmo `operacaoId` | 200 com a mesma resposta, sem debitar de novo |
| Destino fora do ar | derrube a agência 1 e transfira de 8 para 7 com outro `operacaoId` | 200 "publicada". A mensagem fica na `fila-agencia-1` (veja no RabbitMQ Manager). Ao subir de novo, a agência 1 volta sem a conta 7, porque as contas ficam em memória, e o crédito vai para a `fila-mortas` |
| Linha do tempo causal | `python mesclar_logs.py` | Linha do tempo das 3 agências e a lista de pares de eventos concorrentes e causais, calculada pelo relógio vetorial |

### Eleição de líder (Bully)

| Cenário | Comando | Comportamento esperado |
|---|---|---|
| Subida das 3 agências | `curl -s localhost:4071/bully/lider` | `liderAtual: 2`. As três respondem a mesma líder |
| Líder cai | encerre a agência 2 (Ctrl+C) e espere uns 5 s | As agências 0 e 1 registram LIDER_NAO_RESPONDEU e a 1 vira líder |
| Líder antiga volta | suba a agência 2 de novo | A 2 retoma a liderança, porque tem o maior ID |
| Histórico | `python historico_lideranca.py` | Lista das trocas de liderança com horário |

### Sincronização offline-first

| Cenário | Comando | Comportamento esperado |
|---|---|---|
| Sincronizar com vetor atualizado | `V=$(curl -s localhost:4071/contas/8 -H "Authorization: Bearer $T8" \| python -c 'import sys,json;print(json.load(sys.stdin)["vetorAtual"])')` e depois `curl -s -X POST localhost:4071/contas/8/sincronizar -H "Authorization: Bearer $T8" -H 'Content-Type: application/json' -d "{\"tipo\":\"DEPOSITO\",\"valor\":50,\"vetorConhecido\":$V}"` | 200, depósito aplicado |
| Sincronizar com vetor antigo | repita o último comando sem atualizar `$V` | 409 com o `vetorAtual` e a `contaAtual` (saldo real). Nada é aplicado |

### App Flutter

| Cenário | Como fazer | Comportamento esperado |
|---|---|---|
| Painel de liderança | faça login e derrube a agência líder | Em até ~6 s o painel mostra a nova líder, e a troca aparece em "Histórico de líderes" |
| Operação sem conexão | ative o modo avião (ou pare as agências) e faça um depósito | Saldo marcado como "Provisório" e a operação listada como pendente |
| Reconexão | desative o modo avião | A fila é enviada sozinha e o saldo volta a ser confirmado |
| Conflito | offline, deposite pelo app; antes de reconectar, saque da mesma conta pelo curl | Cartão vermelho de conflito com o saldo real e os botões "Descartar" e "Aplicar mesmo assim" |

Os prints desses cenários estão em [`evidencias/`](./evidencias/).
