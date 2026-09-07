# ICEIBank: Contexto de Domínio

Só glossário, sem detalhes de implementação. Este projeto roda ao longo de 4 sprints num único código que evolui; os termos abaixo são do Sprint 1 (REST/MVC + relógio de Lamport).

## Entidades principais

**Agência**: um processo de serviço REST independente. Mesmo código, implantado 3 vezes, distinguido só pelo `AGENCIA_ID` (0, 1, 2). Dona de uma partição de Contas (não uma réplica do banco inteiro), com seu próprio `RelogioLamport` (relógio lógico local) e log de eventos. Agências nunca compartilham memória ou banco de dados; a única forma de uma saber do estado de outra é recebendo uma mensagem dela.

**Conta**: pertence a exatamente uma Agência, decidida por `id_conta % 3`. Campos: `id`, `nomeAluno`, `saldo`. Guardada só em memória (sem persistência neste sprint, reiniciar o processo esvazia tudo).

**Partição**: a regra do enunciado (`id_conta % número_de_agências`) que atribui a cada Conta exatamente uma Agência dona. Diferente de replicação: nenhuma Agência guarda uma segunda cópia das Contas de outra.

**RelogioLamport**: um contador inteiro por Agência, não um relógio de parede. Três operações: `eventoLocal()` (incrementa antes de qualquer evento local), `aoEnviar()` (incrementa e carimba uma mensagem saindo), `aoReceber(t)` (ajusta o contador para `max(local, t) + 1`). Garante que, se A aconteceu antes de B causalmente, `timestamp(A) < timestamp(B)`. Não garante o inverso: timestamps iguais ou fora de ordem podem ser eventos genuinamente concorrentes, sem relação causal nenhuma. Essa lacuna é o que motiva o relógio vetorial no Sprint 2.

**Evento**: um registro imutável de algo que uma Agência fez (`CRIAR_CONTA`, `DEPOSITO`, `SAQUE`, `TRANSFERENCIA_DEBITO`, `TRANSFERENCIA_CREDITO`, `TRANSFERENCIA_CREDITO_REMOTO`, `TRANSFERENCIA_FALHOU`). Carrega `timestampLamport` (o relógio lógico, autoritativo para ordenação) e `horaParede` (relógio físico, só informativo, nunca usado para nenhuma decisão do sistema). Anexado a um log `.jsonl` por Agência, nunca alterado depois.

**Transferência Local**: débito e crédito acontecem dentro do processo da mesma Agência. Nenhuma mensagem atravessa fronteira de processo, então usa só `eventoLocal()`; `aoEnviar()`/`aoReceber()` não se aplicam porque não há envio nem recebimento para marcar.

**Transferência Entre Agências**: o débito acontece localmente (`eventoLocal()`) na Agência de origem, depois uma chamada REST carrega o timestamp de Lamport até a Agência de destino via `aoEnviar()` (origem) / `aoReceber()` (destino). É o único caminho do Sprint 1 em que os relógios de duas Agências realmente interagem.

**Falha Conhecida (inconsistência conhecida)**: se a Agência de destino estiver inacessível no meio de uma transferência, o débito já aplicado não é revertido. Esse é um estado deliberado e dentro do escopo do Sprint 1, não um bug a corrigir; é exatamente a lacuna que o Sprint 4 fecha com 2PC/Saga. A única obrigação deste sprint é registrar a falha (`TRANSFERENCIA_FALHOU`), não repará-la.

**Linha do Tempo Unificada**: uma junção offline dos logs `.jsonl` de todas as Agências, ordenada por `timestampLamport`. Seu propósito é observacional: expor empates de timestamp entre Agências como candidatos a eventos concorrentes (ver a lacuna do RelogioLamport acima).

## Identidade e confiança

**Conta (como principal)**: a entidade Conta também é a identidade de login do JWT, ganhando um campo `senha`; logar como `id_conta` + `senha` é se autenticar como aquela Conta, não como uma pessoa separada que é dona dela. Autenticar como uma Conta só autoriza operar naquela mesma Conta: um token válido da Conta 3 tentando sacar/depositar/consultar/transferir na Conta 7 recebe 403, não 200. Não existe entidade "Cliente" ou "Usuário" neste domínio, ver *Termos evitados de propósito* abaixo e [[0001]].

**Credencial de Serviço**: o mecanismo de confiança para chamadas Agência-a-Agência (`creditar-remoto`). Um segredo compartilhado, conhecido pelos três processos de Agência, verificado via cabeçalho, distinto do JWT de uma Conta. Autentica "esta chamada veio de uma Agência parceira", não "esta chamada veio de uma Conta específica"; de propósito, não é o mesmo conceito de confiança da autenticação de usuário. Ver [[0002]].

## Termos evitados de propósito

**Cliente / Usuário**: considerado e descartado como entidade separada de Conta para o Sprint 1. Introduzi-lo exigiria um diretório mapeando pessoas para Contas que atravessasse Agências, estado que não existe em lugar nenhum desta arquitetura (sem banco, sem memória compartilhada, só partição). Revisitar se um sprint futuro trouxer armazenamento compartilhado ou persistente (Sprint 4, containers); até lá, "a Conta é a identidade" é o modelo deliberado, não um esquecimento.

## Notas de fronteira entre sprints (para você mesmo no futuro, não implementação)

- Ainda não existe banco de dados: as Contas vivem num dicionário local ao processo. O Sprint 4 traz containers, o ponto natural onde persistência apareceria. Não deixe a modelagem de identidade do Sprint 1 pressupor um diretório de usuários compartilhado entre Agências; nenhum existe até lá.
- Só existe relógio de Lamport escalar. O Sprint 2 traz o relógio vetorial especificamente para resolver a lacuna "timestamp igual não é necessariamente concorrente" citada acima; não busque nada parecido com vetor neste sprint.
- A comunicação entre Agências hoje é REST síncrono. O Sprint 2 traz Pub-Sub; o caminho de transferência entre Agências é o mais provável de ser reconstruído sobre mensageria depois, então evite acoplar demais os seus detalhes internos à suposição de que "é uma chamada HTTP" em outras partes do código.
