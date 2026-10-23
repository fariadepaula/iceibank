# ICEIBank: Contexto de Domínio

Só glossário, sem detalhes de implementação. Este projeto roda ao longo de 4 sprints num único código que evolui; os termos abaixo valem a partir do Sprint 2 (mensageria Pub-Sub + relógio vetorial), que evolui o Sprint 1 (REST/MVC + relógio de Lamport).

## Entidades principais

**Agência**: um processo de serviço REST independente. Mesmo código, implantado 3 vezes, distinguido só pelo `AGENCIA_ID` (0, 1, 2). Dona de uma partição de Contas (não uma réplica do banco inteiro), com seu próprio `RelogioVetorial` e log de eventos. Agências nunca compartilham memória ou banco de dados; a única forma de uma saber do estado de outra é recebendo uma mensagem dela, que desde o Sprint 2 chega pelo RabbitMQ.

**Conta**: pertence a exatamente uma Agência, decidida por `id_conta % 3`. Campos: `id`, `nomeAluno`, `saldo`. Guardada só em memória (sem persistência neste sprint, reiniciar o processo esvazia tudo).

**Partição**: a regra do enunciado (`id_conta % número_de_agências`) que atribui a cada Conta exatamente uma Agência dona. Diferente de replicação: nenhuma Agência guarda uma segunda cópia das Contas de outra.

**RelogioVetorial**: um vetor com um contador por Agência (3 posições), substituto do `RelogioLamport` do Sprint 1. `evento_local()` e `ao_enviar()` incrementam a posição da própria Agência; `ao_receber(v)` faz o máximo posição a posição com o vetor recebido e depois incrementa a própria posição. Diferente de Lamport, a comparação vale nos dois sentidos: `V1 <= V2` posição a posição (e diferentes) significa que A aconteceu antes de B; se nenhum dos dois é `<=` ao outro, os eventos são **concorrentes**, sem relação causal nenhuma.

**RelogioLamport** (Sprint 1, aposentado): contador escalar. Garantia só num sentido: causa vem antes de efeito, mas timestamps diferentes não provam causalidade. Essa lacuna motivou o relógio vetorial.

**Evento**: um registro imutável de algo que uma Agência fez (`CRIAR_CONTA`, `DEPOSITO`, `SAQUE`, `TRANSFERENCIA_DEBITO`, `TRANSFERENCIA_CREDITO`, `TRANSFERENCIA_CREDITO_REMOTO`, `CREDITO_REMOTO_FALHOU`, `TRANSFERENCIA_FALHOU`). Carrega `timestampVetorial` (o relógio lógico, autoritativo para causalidade) e `horaParede` (relógio físico, só informativo, nunca usado para nenhuma decisão do sistema). Anexado a um log `.jsonl` por Agência, nunca alterado depois.

**Transferência Local**: débito e crédito acontecem dentro do processo da mesma Agência. Nenhuma mensagem atravessa fronteira de processo, então usa só `eventoLocal()`; `aoEnviar()`/`aoReceber()` não se aplicam porque não há envio nem recebimento para marcar.

**Transferência Entre Agências**: o débito acontece localmente (`evento_local()`) na Agência de origem, que então publica uma mensagem carimbada com `ao_enviar()` na exchange `iceibank.eventos` (routing key `agencia.<destino>.creditar`). A Agência de destino consome da sua fila e aplica `ao_receber()`. É assíncrona: a resposta 200 significa "publicada", não "creditada".

**Fila durável**: cada Agência tem a sua (`fila-agencia-<id>`). Uma mensagem publicada para uma Agência fora do ar fica retida até ela voltar. Isso resolve a perda da mensagem, não a perda do estado: as Contas continuam em memória, então uma Agência que reinicia volta sem as Contas e o crédito não tem onde ser aplicado.

**Fila de mensagens mortas (dead-letter)**: `fila-mortas`, alimentada pela exchange `iceibank.mortas`. Recebe créditos que o consumidor rejeitou (conta não encontrada, mensagem malformada), em vez de descartá-los.

**Falha Conhecida (inconsistência conhecida)**: no Sprint 1, uma Agência de destino inacessível deixava o débito aplicado sem crédito. No Sprint 2 a mensagem não se perde mais, mas o crédito ainda pode não ser aplicável (conta sumida após reinício) e nada devolve o valor à origem. A correção de verdade (compensação) continua sendo assunto do Sprint 4 (2PC/Saga).

**Linha do Tempo Causal**: uma junção offline dos logs `.jsonl` de todas as Agências, exibida pela hora de parede (só para leitura) e analisada pelos vetores: lista os pares de eventos de Agências diferentes que são comprovadamente concorrentes e os que são causalmente relacionados.

## Identidade e confiança

**Conta (como principal)**: a entidade Conta também é a identidade de login do JWT, ganhando um campo `senha`; logar como `id_conta` + `senha` é se autenticar como aquela Conta, não como uma pessoa separada que é dona dela. Autenticar como uma Conta só autoriza operar naquela mesma Conta: um token válido da Conta 3 tentando sacar/depositar/consultar/transferir na Conta 7 recebe 403, não 200. Não existe entidade "Cliente" ou "Usuário" neste domínio, ver *Termos evitados de propósito* abaixo e [[0001]].

**Credencial de Serviço**: o mecanismo de confiança para chamadas de sistema (`POST /contas`, e no Sprint 1 também `creditar-remoto`, removida no Sprint 2). Um segredo compartilhado, conhecido pelos três processos de Agência, verificado via cabeçalho, distinto do JWT de uma Conta. Autentica "esta chamada veio de uma Agência parceira", não "esta chamada veio de uma Conta específica"; de propósito, não é o mesmo conceito de confiança da autenticação de usuário. Ver [[0002]].

## Termos evitados de propósito

**Cliente / Usuário**: considerado e descartado como entidade separada de Conta para o Sprint 1. Introduzi-lo exigiria um diretório mapeando pessoas para Contas que atravessasse Agências, estado que não existe em lugar nenhum desta arquitetura (sem banco, sem memória compartilhada, só partição). Revisitar se um sprint futuro trouxer armazenamento compartilhado ou persistente (Sprint 4, containers); até lá, "a Conta é a identidade" é o modelo deliberado, não um esquecimento.

## Notas de fronteira entre sprints (para você mesmo no futuro, não implementação)

- Ainda não existe banco de dados: as Contas e o próprio relógio vetorial vivem em memória. O Sprint 4 traz containers, o ponto natural onde persistência apareceria.
- O consumidor RabbitMQ não verifica JWT: a confiança hoje é "quem tem a `RABBITMQ_URL` pode publicar". Ver ADR 0002.
- Créditos remotos não confirmam de volta para a origem. Quando o Sprint 4 trouxer Saga, a `fila-mortas` é o ponto natural para disparar a compensação.
