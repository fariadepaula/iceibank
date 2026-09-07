# Respostas — Sprint 1

## Parte B — Relógio de Lamport

**Por que `max(local, recebido) + 1` e não adotar o recebido diretamente?** Porque o relógio precisa refletir *todo* o histórico causal que o processo já viu, não só a mensagem mais recente. Se eu simplesmente adotasse o valor recebido, um evento local que já aconteceu antes de eu receber a mensagem (e que tem um timestamp maior que o recebido) passaria a ter timestamp maior que um evento que veio depois dele causalmente — quebrando a garantia de que causa vem antes de efeito. O `+1` garante que o evento de recepção seja estritamente posterior a ambos: ao que eu já tinha visto e à mensagem que acabei de receber.

**Agência 0 no contador 10 recebe timestamp 3 — qual o novo valor?** `max(10, 3) + 1 = 11`. O contador da agência mais rápida não recua nunca — ela ignora timestamps atrasados na prática (o `max` os torna irrelevantes) e segue avançando a partir de si mesma. Implicação: uma agência que processa muitos eventos rapidamente "puxa" o relógio lógico do sistema para frente; uma agência lenta que manda uma mensagem atrasada não consegue arrastar as outras para trás — o relógio de Lamport é monotônico por construção, nunca diminui.

## Parte D — Transferências

**Por que a transferência local não usa `ao_enviar()`/`ao_receber()`?** Porque essas duas operações existem para carimbar uma mensagem que atravessa a fronteira de um processo — é assim que o relógio de Lamport propaga causalidade entre processos diferentes. Numa transferência local, débito e crédito acontecem dentro do mesmo processo, na mesma thread, sem nenhuma mensagem sendo enviada a lugar nenhum: os dois são só `evento_local()`. Só existe "enviar" e "receber" quando duas agências (dois relógios lógicos independentes) precisam sincronizar via uma chamada de rede.

**A falha conhecida foi reproduzida (ver `evidencias/sprint1/falha-conhecida.png`): o saldo foi revertido?** Não. Derrubei a Agência 1 e tentei transferir R$5 da conta 0 (Agência 0) para a conta 1. A resposta foi 502 e o saldo da conta 0 caiu de 50 para 45 — o débito ficou aplicado, o crédito nunca aconteceu porque a chamada remota falhou, e nada desfez o débito. Em termos de consistência bancária: o sistema perdeu a propriedade de atomicidade da transação (tudo-ou-nada). R$5 saíram de uma conta e não entraram em nenhuma outra — dinheiro "sumiu" do sistema como um todo, o que é inaceitável num banco real, mas é exatamente o gap que este sprint deixa aberto de propósito.

**Duas formas de corrigir isso no Sprint 4 (alto nível):**
1. **Two-Phase Commit (2PC):** a agência de origem não debita direto — ela pergunta primeiro às agências envolvidas "você consegue confirmar esta operação?" (fase de preparação), só aplica o débito e o crédito depois que todas confirmarem que podem, e desfaz tudo (rollback) se qualquer uma disser que não pode ou não responder.
2. **Saga (compensação):** a operação é dividida em passos locais independentes, cada um com uma "ação compensatória" definida (ex.: se o crédito remoto falhar, dispara-se automaticamente um evento `TRANSFERENCIA_COMPENSACAO` que credita de volta a conta de origem) — em vez de travar as duas agências esperando confirmação mútua, aceita-se a inconsistência temporária e ela é corrigida logo em seguida por um passo compensador.

## Parte E — Linha do tempo

Rodando `mesclar_logs.py` sobre os logs gerados pelos testes da Parte D apareceu um empate real, sem eu precisar forçar nada: `[Lamport 7]` aparece duas vezes — uma para `agencia-0 TRANSFERENCIA_DEBITO` (o débito de R$5 da segunda transferência, que depois falhou) e outra para `agencia-1 TRANSFERENCIA_CREDITO_REMOTO` (o crédito de R$30 da primeira transferência, que tinha sido bem-sucedida). São eventos genuinamente concorrentes: a Agência 0 debitando para uma operação nova não tem nenhuma relação causal com a Agência 1 creditando o resultado de uma operação anterior e já concluída — cada relógio simplesmente chegou em 7 pelo seu próprio caminho, por coincidência. Comparando `horaParede`: o evento da Agência 1 tem timestamp físico *anterior* (16:17:45.675) ao da Agência 0 (16:17:46.744) — quase um segundo antes, mesmo com Lamport empatado. Ou seja, mesmo quebrando o empate pela hora de parede, isso não teria significado causal nenhum: são dois eventos que não se comunicaram entre si, o empate no relógio lógico só reflete que nenhum "aconteceu antes" do outro, não que aconteceram ao mesmo tempo real.

**O que isso significa na prática ao ver dois timestamps diferentes (não empatados) na linha do tempo?** `timestamp(A) < timestamp(B)` só me diz que B *pode* ter acontecido depois de A causalmente, ou que simplesmente não têm relação alguma — o relógio de Lamport nunca prova a ausência de causalidade, só a garante quando ela existe. Vendo dois timestamps diferentes eu não consigo, só com esse número, distinguir "A causou B" de "A e B são concorrentes e por acaso o contador de quem gerou B já estava mais adiantado".

**O relógio de Lamport sozinho seria suficiente para distinguir com certeza concorrência de precedência causal?** Não — e o empate acima é a prova prática disso: dois eventos sem relação nenhuma caíram no mesmo número, mas o inverso também falha (dois eventos concorrentes podem receber timestamps diferentes, sem que isso signifique que um causou o outro). Um contador escalar colapsa toda a informação causal em um único inteiro, perdendo a estrutura de "quem viu o quê". É exatamente essa ambiguidade que motiva o relógio vetorial do Sprint 2: em vez de um inteiro, cada processo mantém um vetor com o conhecimento causal de todos os outros, permitindo comparar dois eventos e saber com certeza se um precede o outro ou se são genuinamente concorrentes.

## Parte F — Autenticação JWT

**Formato das credenciais:** `id_conta` + `senha` (senha adicionada à própria Conta, hash com PBKDF2-HMAC-SHA256 + salt aleatório via `hashlib`, sem dependência nova). A Conta *é* a identidade — não existe um "Cliente" separado nesta arquitetura (partição, sem estado compartilhado entre agências); ver [ADR 0001](docs/adr/0001-conta-is-the-jwt-principal.md).

**Expiração:** 20 minutos para tokens de conta (uso humano via frontend), 24 horas para tokens de serviço (uso automatizado entre processos — ver abaixo). Nenhum dos dois é eterno.

**Chamada `creditar-remoto` entre agências — mesmo JWT do usuário ou tratamento próprio?** Tratamento próprio: um token de serviço (`tipo: servico` no payload, sem `sub`), assinado com o mesmo segredo compartilhado pelas 3 agências, mas representando "esta chamada vem de uma agência parceira confiável", não "esta chamada vem do usuário X". Reusar o JWT do usuário acoplaria uma chamada interna de sistema à sessão de uma pessoa, sem necessidade. Essa mesma credencial de serviço também protege `POST /contas`: como toda rota que cria ou modifica uma conta precisa de um token válido, e criar conta é logicamente "antes" de qualquer pessoa conseguir logar (não existe usuário ainda para emitir um token de conta), tratei a criação de conta como uma operação de provisionamento do sistema, não uma ação de autoatendimento — gera-se um token de serviço localmente (`python mint_service_token.py`) para isso. Ver [ADR 0002](docs/adr/0002-service-credential-for-inter-agencia-calls.md).

**Autenticação vs. autorização — a implementação verifica as duas?** Sim. Autenticação é `principal_atual()`: prova que o token é válido, não expirou e foi assinado com o segredo certo (401 se falhar). Autorização é o passo seguinte, em `exigir_dono_da_conta()`: mesmo com um token de conta válido, comparo `sub` do token com o `id` da conta que a rota está tentando acessar (403 se não bater). Testei ao vivo: um token da conta 0 tentando sacar da conta 1 recebe 403, mesmo sendo um token perfeitamente válido — autenticado, mas não autorizado para aquela conta.

**Por que não é preciso consultar banco a cada requisição para validar o JWT?** Porque a assinatura HMAC é verificável matematicamente com o mesmo segredo que a gerou — se o token não foi alterado desde que a agência o assinou, a verificação local (`jwt.decode`) já garante isso, sem round-trip nenhum a um armazenamento externo. Isso é o que permite cada agência validar tokens de forma totalmente independente, sem nenhuma tabela de sessões compartilhada entre elas — essencial aqui, já que as 3 agências não compartilham nenhum estado.

**Se o segredo do JWT vazasse:** qualquer pessoa poderia forjar um token válido para *qualquer* conta (bastaria assinar `{"sub": "<qualquer id>", "tipo": "conta"}` com o segredo vazado) — e, pior, também forjar tokens de serviço, contornando inclusive a proteção de `criar-conta` e `creditar-remoto`. Seria um comprometimento total do sistema de autenticação, não apenas de uma conta.

## Parte G — Frontend

_A preencher ao concluir a Parte G._

## Funcionalidade adicional

_A preencher junto do commit da funcionalidade adicional._
