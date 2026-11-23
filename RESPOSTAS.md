# Respostas do Sprint 1

## Parte B: Relógio de Lamport

**Por que `max(local, recebido) + 1` e não adotar o recebido diretamente?** Porque o relógio precisa refletir todo o histórico causal que o processo já viu, não só a mensagem mais recente. Se eu adotasse o valor recebido, um evento local que já aconteceu antes de eu receber a mensagem, e que tem timestamp maior que o recebido, passaria a ter timestamp maior que um evento que veio depois dele causalmente. Isso quebraria a garantia de que causa vem antes de efeito. O `+1` garante que o evento de recepção seja estritamente posterior aos dois: ao que eu já tinha visto e à mensagem que acabei de receber.

**Agência 0 no contador 10 recebe timestamp 3, qual o novo valor?** `max(10, 3) + 1 = 11`. O contador da agência mais rápida não recua nunca: ela ignora timestamps atrasados na prática, já que o `max` os torna irrelevantes, e segue avançando a partir de si mesma. Uma agência que processa muitos eventos rapidamente puxa o relógio lógico do sistema para frente; uma agência lenta que manda uma mensagem atrasada não consegue arrastar as outras para trás. Por construção, o relógio de Lamport nunca diminui.

## Parte D: Transferências

**Por que a transferência local não usa `ao_enviar()`/`ao_receber()`?** Porque essas duas operações existem para carimbar uma mensagem que atravessa a fronteira de um processo, é assim que o relógio de Lamport propaga causalidade entre processos diferentes. Numa transferência local, débito e crédito acontecem dentro do mesmo processo, na mesma thread, sem nenhuma mensagem sendo enviada a lugar nenhum: os dois são só `evento_local()`. Só existe enviar e receber quando duas agências, com relógios lógicos independentes, precisam sincronizar via uma chamada de rede.

**A falha conhecida foi reproduzida (ver `evidencias/sprint1/falha-conhecida.png`): o saldo foi revertido?** Não. Derrubei a Agência 1 e tentei transferir R$5 da conta 0 (Agência 0) para a conta 1. A resposta foi 502 e o saldo da conta 0 caiu de 50 para 45: o débito ficou aplicado, o crédito nunca aconteceu porque a chamada remota falhou, e nada desfez o débito. Em termos de consistência bancária, o sistema perdeu a propriedade de atomicidade da transação (tudo ou nada). R$5 saíram de uma conta e não entraram em nenhuma outra, dinheiro sumiu do sistema como um todo. Isso é inaceitável num banco real, mas é o gap que este sprint deixa aberto de propósito.

**Duas formas de corrigir isso no Sprint 4 (alto nível):**

1. **Two-Phase Commit (2PC):** a agência de origem não debita direto. Ela pergunta primeiro às agências envolvidas se conseguem confirmar a operação (fase de preparação), só aplica o débito e o crédito depois que todas confirmarem, e desfaz tudo (rollback) se qualquer uma disser que não pode ou não responder.
2. **Saga (compensação):** a operação é dividida em passos locais independentes, cada um com uma ação compensatória definida. Por exemplo, se o crédito remoto falhar, dispara-se automaticamente um evento `TRANSFERENCIA_COMPENSACAO` que credita de volta a conta de origem. Em vez de travar as duas agências esperando confirmação mútua, aceita-se a inconsistência temporária e ela é corrigida logo em seguida por um passo compensador.

## Parte E: Linha do tempo

Rodando `mesclar_logs.py` sobre os logs gerados pelos testes da Parte D apareceu um empate real, sem eu precisar forçar nada. `[Lamport 7]` aparece duas vezes: uma para `agencia-0 TRANSFERENCIA_DEBITO` (o débito de R$5 da segunda transferência, que depois falhou) e outra para `agencia-1 TRANSFERENCIA_CREDITO_REMOTO` (o crédito de R$30 da primeira transferência, que já tinha sido bem-sucedida). São eventos concorrentes. A Agência 0 debitando para uma operação nova não tem relação causal nenhuma com a Agência 1 creditando o resultado de uma operação anterior já concluída. Cada relógio chegou em 7 pelo seu próprio caminho, por coincidência. Comparando `horaParede`, o evento da Agência 1 tem timestamp físico anterior (16:17:45.675) ao da Agência 0 (16:17:46.744), quase um segundo antes, mesmo com Lamport empatado. Mesmo quebrando o empate pela hora de parede, isso não teria significado causal nenhum, porque são dois eventos que não se comunicaram entre si. O empate no relógio lógico só reflete que nenhum aconteceu antes do outro, não que aconteceram ao mesmo tempo real.

**O que isso significa na prática ao ver dois timestamps diferentes (não empatados) na linha do tempo?** `timestamp(A) < timestamp(B)` só diz que B pode ter acontecido depois de A causalmente, ou que não têm relação alguma. O relógio de Lamport nunca prova a ausência de causalidade, só a garante quando ela existe. Vendo dois timestamps diferentes, não dá para distinguir só com esse número se A causou B ou se A e B são concorrentes e por acaso o contador de quem gerou B já estava mais adiantado.

**O relógio de Lamport sozinho seria suficiente para distinguir com certeza concorrência de precedência causal?** Não, e o empate acima é a prova prática disso: dois eventos sem relação nenhuma caíram no mesmo número. O inverso também falha, já que dois eventos concorrentes podem receber timestamps diferentes sem que isso signifique que um causou o outro. Um contador escalar colapsa toda a informação causal num único inteiro, perdendo a estrutura de quem viu o quê. Essa ambiguidade é o que motiva o relógio vetorial do Sprint 2: em vez de um inteiro, cada processo mantém um vetor com o conhecimento causal de todos os outros, permitindo comparar dois eventos e saber com certeza se um precede o outro ou se são concorrentes.

## Parte F: Autenticação JWT

**Formato das credenciais:** `id_conta` + `senha`, com a senha adicionada à própria Conta e o hash calculado com PBKDF2-HMAC-SHA256 mais salt aleatório via `hashlib`, sem dependência nova. A Conta é a identidade: não existe um "Cliente" separado nesta arquitetura, já que as agências não compartilham estado entre si. Ver [ADR 0001](docs/adr/0001-conta-is-the-jwt-principal.md).

**Expiração:** 20 minutos para tokens de conta, usados pelo frontend, e 24 horas para tokens de serviço, usados entre processos (ver abaixo). Nenhum dos dois é eterno.

**Chamada `creditar-remoto` entre agências, mesmo JWT do usuário ou tratamento próprio?** Tratamento próprio. Um token de serviço, com `tipo: servico` no payload e sem `sub`, assinado com o mesmo segredo compartilhado pelas 3 agências, representa "esta chamada vem de uma agência parceira confiável", não "esta chamada vem do usuário X". Reusar o JWT do usuário acoplaria uma chamada interna de sistema à sessão de uma pessoa sem necessidade. Essa mesma credencial de serviço também protege `POST /contas`. Como toda rota que cria ou modifica uma conta precisa de um token válido, e criar conta é logicamente anterior a qualquer pessoa conseguir logar (ainda não existe usuário para emitir um token de conta), tratei a criação de conta como uma operação de provisionamento do sistema, não uma ação de autoatendimento. O token de serviço para isso é gerado localmente com `python mint_service_token.py`. Ver [ADR 0002](docs/adr/0002-service-credential-for-inter-agencia-calls.md).

**Autenticação vs. autorização, a implementação verifica as duas?** Sim. Autenticação é `principal_atual()`: prova que o token é válido, não expirou e foi assinado com o segredo certo, 401 se falhar. Autorização é o passo seguinte, em `exigir_dono_da_conta()`: mesmo com um token de conta válido, comparo `sub` do token com o `id` da conta que a rota está tentando acessar, 403 se não bater. Testei ao vivo: um token da conta 0 tentando sacar da conta 1 recebe 403, mesmo sendo um token válido.

**Por que não é preciso consultar banco a cada requisição para validar o JWT?** Porque a assinatura HMAC é verificável matematicamente com o mesmo segredo que a gerou. Se o token não foi alterado desde que a agência o assinou, a verificação local com `jwt.decode` já garante isso, sem round-trip nenhum a um armazenamento externo. Isso é o que permite cada agência validar tokens de forma totalmente independente, sem tabela de sessões compartilhada entre elas. Aqui isso é obrigatório, porque as 3 agências não compartilham nenhum estado.

**Se o segredo do JWT vazasse:** qualquer pessoa poderia forjar um token válido para qualquer conta, bastando assinar `{"sub": "<qualquer id>", "tipo": "conta"}` com o segredo vazado. Pior, também daria para forjar tokens de serviço, contornando a proteção de `criar-conta` e `creditar-remoto`.

## Parte G: Frontend

**Como o frontend reenvia o token depois do login?** Um objeto reativo simples (`src/auth.js`, exportado como `auth`) guarda `token`, `contaId` e `agencia`, sincronizado com `localStorage` via `watch()`. Uma função central `api()` (`src/api.js`) é usada por todos os componentes para chamar o backend: ela lê `auth.token` e injeta `Authorization: Bearer <token>` no cabeçalho de toda chamada que precisa de autenticação. Não usei Axios nem Pinia, um `fetch` nativo com essa função de uma dezena de linhas cobre o que interceptors fariam, sem dependência nova.

**Se o token expirar no meio do uso, o que acontece?** A função `api()` verifica `resposta.status === 401` antes de qualquer outra coisa. Se acontecer, ela limpa o token (`logout()`), o que faz o `App.vue` trocar automaticamente do Dashboard de volta para a tela de login, de forma reativa, sem precisar de reload, e lança um erro com uma mensagem legível ("Sessão expirada, faça login novamente.") que o componente exibe na tela.

**Onde ficam Model, View e Controller no frontend?** `src/auth.js` é o Model do lado de autenticação, guardando estado e persistência. Os dados de saldo e nome vivem como `ref()` dentro do próprio componente que os usa, então o Model está parcialmente misturado com a View, já que não criei uma camada de modelo separada para "Conta" no frontend (ela só existe como resposta de uma chamada, sem estado complexo próprio). `LoginView.vue` e `Dashboard.vue` são a View. O Controller é `src/api.js`: toda a lógica de comunicação com o backend, tratamento de erro e formatação de request/response fica ali, fora dos componentes, que só chamam `api(...)` e reagem ao resultado. A separação entre Controller e View é real, mas o Model é o ponto mais fraco: para telas mais complexas eu criaria um módulo de domínio próprio em vez de deixar os dados como `ref()` local do componente.

## Funcionalidade adicional

**Idempotência de transferências.** `POST /transferencias` e `POST /contas/{id}/creditar-remoto` aceitam um campo opcional `operacaoId`, uma string gerada pelo cliente (por exemplo um UUID). Cada agência guarda em memória (`app.state.operacoes_vistas`) o resultado já produzido para cada `operacaoId` visto. Se a mesma requisição chegar de novo com o mesmo `operacaoId`, seja por reenvio de timeout do cliente, retry de rede ou duplo clique no frontend, a agência devolve a resposta já registrada em vez de reaplicar o débito ou crédito.

**Por que escolhi essa:** é a funcionalidade da lista que mais se conecta ao resto do projeto. A limitação conhecida da Parte D, débito sem reversão automática, é sobre uma operação falhar parcialmente. Idempotência é sobre o outro lado do mesmo problema de rede não confiável: uma operação que pareceu falhar por timeout, mas só demorou a responder, levando o cliente a tentar de novo. Sem uma chave de idempotência, esse retry dobraria o valor transferido. É o tipo de garantia que o Sprint 4 vai precisar para implementar 2PC/Saga corretamente, já que cada passo compensador só é seguro de reexecutar se for idempotente.

**Evidência:** validei via curl enviando a mesma transferência entre agências duas vezes com `operacaoId=op-1`. A segunda chamada devolveu a mesma mensagem de sucesso sem debitar de novo (saldo da conta de origem ficou em 70, não 40). Print em `evidencias/sprint1/funcionalidade-adicional.png`.

# Respostas do Sprint 2

## Parte B: Relógio vetorial

**Com 10 agências, o que acontece com o tamanho do vetor anexado a cada mensagem? É um problema?** O vetor cresce linearmente com o número de processos: com 10 agências, cada mensagem e cada evento do log carregam 10 inteiros em vez de 3. Para 10 isso é irrelevante, são algumas dezenas de bytes num JSON que já carrega valor, ids e origem. O problema aparece em escala: o vetor é O(N) por mensagem, e N tem que ser conhecido de antemão por todo mundo (aqui ele vem de `NUMERO_AGENCIAS` em `config.py`). Num sistema com milhares de processos, ou em que processos entram e saem dinamicamente, o custo de banda e de armazenamento cresce junto e o vetor de tamanho fixo deixa de funcionar. Por isso existem variações como vetores esparsos (só as posições não-zero) e *version vectors* por réplica em vez de por cliente.

**V1 = [3, 1, 0] e V2 = [3, 2, 0]:** V1 aconteceu antes de V2. Posição a posição: 3 <= 3, 1 <= 2, 0 <= 0, todas `<=`, e os vetores são diferentes (posição 1). V2 já "viu" tudo o que V1 viu, mais um evento da agência 1. O autoteste de `vector_clock.py` cobre esse caso (`comparar(...) == "ANTES"`).

**V1 = [3, 1, 0] e V2 = [1, 3, 0]:** são concorrentes. Na posição 0, V1 > V2 (3 > 1); na posição 1, V2 > V1 (3 > 1). Nenhum dos dois é `<=` ao outro em todas as posições: cada um conhece eventos que o outro não conhece, então nenhum pode ter causado o outro. Também coberto pelo autoteste (`"CONCORRENTES"`).

## Parte C: Publish/Subscribe

**O que aconteceu quando a Agência 1 voltou?** Com a conta 1 criada e já tendo recebido R$30, derrubei a Agência 1 e transferi R$5 da conta 0 para a conta 1. A resposta foi 200 ("Transferência publicada... entrega assíncrona") e o saldo da conta 0 caiu de 70 para 65. Com a agência fora do ar, `rabbitmqctl list_queues` mostrou `fila-agencia-1` com 1 mensagem retida. Ao subir a Agência 1 de novo, o log mostrou `[mensageria] consumindo fila-agencia-1` e, logo em seguida, `[Vetor [5, 1, 0]] CREDITO_REMOTO_FALHOU {'idConta': 1, 'valor': 5.0, 'origemAgencia': 0, 'motivo': 'conta não encontrada'}`. A mensagem foi entregue, então a mensageria funcionou. O crédito não foi aplicado porque a conta 1 vivia só na memória do processo que morreu, e o login com ela passou a dar 401. Um detalhe que também aparece nesse log: o vetor da Agência 1 recomeçou do zero. Antes de cair, ela estava em `[3, 3, 0]` e voltou com a própria posição em 1. O relógio também é estado em memória, então o reinício quebra até a monotonicidade do contador da própria agência. Antes da dead-letter (funcionalidade adicional), a mensagem levava ack e sumia. Agora ela vai para `fila-mortas`.

**Comparação com o Sprint 1:** o que melhorou é que a falha de rede ou de disponibilidade deixou de perder a mensagem. No Sprint 1, a chamada REST falhava na hora, com 502, e o crédito nunca era tentado de novo. Agora a fila durável com mensagem persistente segura o crédito até a agência voltar, e quem transfere nem precisa saber que ela caiu. O que continua aberto é que "a mensagem não se perde" não é o mesmo que "o sistema está correto": o débito foi aplicado na origem, o crédito não teve onde ser aplicado no destino e nada devolve os R$5. A atomicidade continua quebrada, só que agora sem o 502 avisando o cliente, que recebe 200 e só descobriria olhando os saldos. Fechar isso exige persistência das contas e uma ação compensatória de volta para a origem (Saga), que é o assunto do Sprint 4.

**O consumidor processa créditos sem verificar JWT: é um problema?** Hoje, no meu ambiente, quem consegue publicar na exchange é quem tem a `RABBITMQ_URL`, que leva usuário e senha da instância. Ela só existe nas variáveis de ambiente das três agências, então a credencial do broker faz o papel da credencial de serviço do Sprint 1 (ver ADR 0002, atualizado). Mas qualquer um com essa URL publica `{"idConta": X, "valor": 1000000, ...}` em `agencia.N.creditar` e cria dinheiro do nada, porque o consumidor confia cegamente no conteúdo. A mensagem não é assinada, e o `origemAgencia` é só um campo que qualquer um preenche. Em produção eu usaria um usuário do RabbitMQ por agência com permissão de escrita restrita, mais uma assinatura HMAC da mensagem (o mesmo segredo compartilhado que já assina os tokens de serviço), verificada no consumidor antes de aplicar o crédito.

## Parte D: Linha do tempo causal

**O que torna a comparação confiável no relógio vetorial?** O vetor guarda, por agência, quantos eventos dela já influenciaram o evento atual, em vez de colapsar tudo num inteiro só. Com isso, "A aconteceu antes de B" passa a ser equivalente a `V(A) <= V(B)` posição a posição, nos dois sentidos: se A causou B, o vetor de B domina o de A, e se o vetor de B domina o de A, então existe uma cadeia de mensagens levando A até B. No Lamport só valia a ida. Por isso a ausência de dominância em qualquer direção prova que os eventos são concorrentes, que é o que `comparar()` em `vector_clock.py` verifica.

**Um par concorrente do meu teste:** `[agencia-1] CRIAR_CONTA [0, 1, 0]` (conta 4) x `[agencia-2] CRIAR_CONTA [0, 0, 1]` (conta 5). Faz sentido: são duas contas criadas em agências diferentes, sem nenhuma mensagem trocada entre a Agência 1 e a Agência 2. O vetor da Agência 1 tem 0 na posição 2 (nunca soube de nada da Agência 2), e o da Agência 2 tem 0 na posição 1. Cada um só conhece o próprio evento. Pela hora de parede, uma foi criada cerca de 70ms depois da outra, e o script corretamente ignora isso. Outro par concorrente do mesmo teste é menos óbvio: `[agencia-1] TRANSFERENCIA_CREDITO_REMOTO [3, 3, 0]` x `[agencia-0] TRANSFERENCIA_DEBITO [4, 0, 0]`. A Agência 0 debitou a segunda transferência sem ter recebido nenhuma mensagem da Agência 1 (posição 1 em 0), então o crédito da primeira não influenciou esse débito, mesmo tendo acontecido antes no tempo real. Já o par débito `[agencia-0] TRANSFERENCIA_DEBITO [2, 0, 0]` → `[agencia-1] TRANSFERENCIA_CREDITO_REMOTO [3, 3, 0]` aparece na lista de pares causais, e não na de concorrentes, porque o crédito só existiu por causa da mensagem enviada após o débito.

**O(n²) seria um problema com milhões de eventos?** Seria: 10^6 eventos dão ~5·10^11 comparações de vetor, inviável para um script. Algumas saídas: comparar só eventos dentro de uma janela (de tempo ou de N eventos por agência), já que concorrência interessa entre eventos próximos; aproveitar que os eventos de uma mesma agência já são totalmente ordenados pela própria posição do vetor, o que permite, para cada evento, achar por busca binária na sequência de cada outra agência a fronteira entre "antes", "concorrente" e "depois", em vez de comparar com todos; ou contar os pares concorrentes em vez de listá-los, já que a lista em si é O(n²) no pior caso.

## Funcionalidade adicional: fila dead-letter

**O que é:** as filas `fila-agencia-0..2` são declaradas com `x-dead-letter-exchange = iceibank.mortas`, uma exchange fanout ligada à fila durável `fila-mortas`. O consumidor confirma (ack) a mensagem só se o crédito foi aplicado. Se `aplicar_credito_remoto` devolve `False` (conta não encontrada) ou o processamento lança exceção (mensagem malformada), ele faz `basic_nack(requeue=False)`, e o RabbitMQ move a mensagem para `fila-mortas` com o conteúdo original intacto, em vez de descartá-la.

**Por que escolhi essa:** ela fecha o buraco exato que o teste de resiliência da Parte C expôs. Sem ela, o crédito de R$5 para a conta que sumiu com o reinício levava ack e desaparecia: a única prova de que existiu era uma linha de log. Com ela, o dinheiro "em trânsito" fica retido e inspecionável no broker (`idConta`, `valor`, `vetorEnvio`, `origemAgencia`, `idOrigem`), e pode ser reprocessado ou usado para estornar a origem. É o ponto de partida natural para a compensação da Saga no Sprint 4. Também protege o consumidor de *poison messages*: sem o nack, uma mensagem malformada derrubaria o consumo e voltaria para a fila a cada reconexão.

**Evidência:** no mesmo cenário da Parte C, depois que a Agência 1 voltou, `fila-mortas` ficou com 1 mensagem, `{"idConta": 1, "valor": 5.0, "vetorEnvio": [5, 0, 0], "origemAgencia": 0, "idOrigem": 0, ...}`, e as três filas das agências ficaram vazias. Print em `evidencias/sprint2/funcionalidade-adicional.png`.

# Respostas do Sprint 3

## Parte A: Mensagens de eleição e coordenador

**Por que o Bully elege o maior ID, e não o menor? O resultado mudaria com a regra invertida?** A regra só precisa ser uma ordem total que todas as agências conheçam de antemão, para que todas cheguem à mesma resposta sem negociar. "Maior ID vence" é a convenção do artigo do Garcia-Molina. Com "menor ID vence", o algoritmo continuaria correto: cada agência mandaria a eleição para as de ID menor, e a agência 0 seria a líder sempre que estivesse no ar, com todas concordando sobre isso do mesmo jeito.

**Mais de uma agência declarou TORNOU_LIDER na subida. É bug ou comportamento esperado?** No meu teste (`evidencias/sprint3/eleicao-inicial.png`) só a agência 2 declarou TORNOU_LIDER, mas declarou três vezes nos primeiros segundos, e a agência 0 recebeu três anúncios de coordenador. É esperado. Cada agência dispara a própria eleição ao subir, e cada eleição recebida de alguém menor também dispara uma nova eleição. A agência 2 não tem ninguém acima dela, então toda eleição que ela roda termina com ela anunciando de novo. Se a agência 1 tivesse subido segundos antes da 2, ela teria se declarado líder antes de a 2 existir, e depois a 2 tomaria o lugar. O algoritmo converge porque a regra é a mesma para todo mundo, e o maior ID ativo sempre anuncia por último.

**O `/bully/eleicao` não tem autenticação. Isso é um problema real?** Neste projeto o risco é pequeno, porque as agências rodam na minha máquina e as portas não ficam expostas. Mas o problema existe. Qualquer processo que conheça a URL pode mandar eleições em loop e manter as agências ocupadas, e o `/bully/coordenador` é pior, porque um POST com `{"liderId": 0}` faz uma agência aceitar uma líder falsa até o próximo heartbeat. Quando a líder passar a coordenar transações no Sprint 4, isso vira um problema sério. A correção é a mesma das chamadas entre agências do Sprint 1: exigir o token de serviço nas rotas `/bully/*`.

## Parte B: Heartbeat e failover automático

**Intervalo muito curto (100 ms) ou muito longo (60 s)?** Com 100 ms, cada agência faria 10 GETs por segundo na líder, e a líder, com mais agências, passaria boa parte do tempo respondendo heartbeat. Uma resposta atrasada por um pico de carga também dispararia eleições sem a líder ter caído. Com 60 s, a líder poderia ficar fora do ar por até um minuto sem ninguém perceber. Com os 3 s que usei, a detecção no teste levou cerca de 3 s: derrubei a agência 2 às 14:24:41 e as agências 0 e 1 registraram LIDER_NAO_RESPONDEU às 14:24:44.

**A agência derrubada volta e toma a liderança de volta. Isso é desejável?** Não costuma ser. No teste, a agência 2 voltou e a liderança saiu da 1 para a 2 sem nenhum problema com a 1. Isso é uma eleição a mais, com troca de mensagens, por um motivo que não melhora nada. Se essa troca acontecer no meio de uma transação coordenada pela líder (2PC no Sprint 4), a líder antiga pode ter mandado o "prepare" e a nova não saber disso, deixando participantes travados esperando um commit que ninguém vai mandar. O Raft, por exemplo, não troca de líder enquanto a atual responde, e usa um número de mandato (term) para descartar ordens de uma líder antiga.

**E se a rede estiver lenta e a resposta passar de 1 s?** A agência trataria uma líder viva como morta. Ela marcaria LIDER_NAO_RESPONDEU e começaria uma eleição. Se a lentidão for para a agência de maior ID, as menores podem não receber resposta dela a tempo e se declarar líderes, e o sistema fica com duas líderes até a resposta da maior chegar e ela anunciar de novo. O timeout de 1 s não distingue "caiu" de "está lento". Num sistema real ele seria configurado com base na latência medida, ou exigiria algumas falhas seguidas antes de declarar a líder morta.

## Parte C: Observando a eleição

**Quantas vezes a liderança mudou de mãos durante a subida? Isso tem custo?** Nenhuma. A agência 2 foi a líder desde o primeiro TORNOU_LIDER, mas o anunciou três vezes, e a saída do `historico_lideranca.py` mostra três linhas "Agência 2 é a líder" no mesmo segundo (17:22:17 UTC). O resultado final não muda, mas cada repetição custa mensagens: cada TORNOU_LIDER manda um POST `/bully/coordenador` para as outras duas agências, então foram 6 anúncios onde 2 bastariam, mais as mensagens de eleição que causaram cada um. Cada eleição também espera até 1 s por agência que não responde, o que atrasa a convergência na subida.

## Parte D: App Flutter

**Com que frequência o app consulta `/bully/lider`, e qual foi o trade-off?** A cada 3 s, o mesmo intervalo do heartbeat do backend. Consultar mais rápido não adianta, porque o backend leva cerca de 3 s para perceber a queda e eleger outra líder. No teste, derrubei a líder e o painel mudou para a Agência 1 cerca de 3 s depois (14:23:44 no backend, 14:23:47 no app). Num celular de verdade, uma consulta pequena a cada 3 s com a tela aberta me pareceu aceitável.

**E se duas agências responderem líderes diferentes durante a transição?** O app mostra o que a agência consultada respondeu, junto com o nome dela ("segundo a Agência 0"). Ele continua consultando a mesma agência enquanto ela responder, então o painel não fica alternando entre respostas de agências diferentes. Se essa agência ainda não souber da nova eleição, o painel mostra a líder antiga por um ou dois ciclos e corrige na consulta seguinte, assim que o anúncio de coordenador chegar nela. Para o painel isso não é um problema. Seria um problema se o app usasse a líder para decidir para onde mandar uma operação, o que ele não faz.

**O que deu para reaproveitar do frontend web e o que mudou no mobile?** A estrutura é a mesma do Sprint 1. O `auth.js` virou a classe `Sessao`, e o `api.js` virou o `ApiClient`, que injeta o token, trata 401 voltando para o login e transforma o `detail` da API em mensagem na tela. O que mudou:
- O token fica no `shared_preferences` em vez do `localStorage`.
- O app não tem um seletor de agência. Ele tenta as 3 em sequência, porque num celular a rede cai com mais frequência. Para não aplicar uma operação duas vezes, ele só repete um POST noutra agência se a conexão foi recusada.
- No Android, `localhost` é o próprio celular, então o endereço das agências é configurável (`10.0.2.2` no emulador), e o manifesto precisou liberar HTTP sem TLS.
- O modo offline da Parte F não tem equivalente no frontend web.

## Parte E: Sincronização offline-first no backend

**Por que comparar o vetor inteiro, e não só ver se o saldo mudou?** Porque o saldo pode voltar ao mesmo valor depois de várias operações. Se alguém deposita R$50 e saca R$50 enquanto o app está offline, o saldo é o mesmo, mas o app não sabe que essas operações aconteceram, e a decisão dele (um saque, por exemplo) foi tomada sem elas. O vetor avança a cada evento da agência, então qualquer operação no meio aparece na comparação. No teste (`conflito-sincronizacao.png`), o depósito de R$50 levou o vetor de `[15,28,14]` para `[15,29,14]`, e a sincronização com o vetor antigo recebeu 409.

**Qualquer mudança no vetor da agência vira conflito, mesmo de outra conta. Por que essa simplificação, e como deixar a detecção por conta?** O relógio vetorial é da agência, e uma operação em qualquer conta da partição avança o mesmo vetor. No meu código, até as mensagens do Bully avançam o vetor, porque `receber_coordenador` chama `ao_receber`. Então uma troca de líder enquanto o app está offline também gera 409, mesmo sem ninguém mexer na conta. A simplificação existe porque o vetor já estava pronto do Sprint 2 e não exige guardar nada novo. Para detectar por conta, cada conta precisaria de uma versão própria, um contador que só avança em operações daquela conta e é devolvido junto com o saldo. O app mandaria essa versão no lugar do vetor, e a agência recusaria só se a versão da conta tivesse mudado.

**O que o app deve fazer com o 409: descartar, tentar de novo sozinho ou perguntar?** Escolhi perguntar. A operação offline foi decidida em cima de um saldo que não existe mais. No meu teste, o app achava que a conta tinha R$580 e, por fora, alguém sacou R$200. Reaplicar sozinho poderia executar um saque que a pessoa não faria se soubesse do saldo real, e descartar sozinho faria um depósito sumir sem aviso. Por isso o app mostra o saldo real e deixa a pessoa escolher entre "Descartar" e "Aplicar mesmo assim".

## Parte F: App Flutter, modo offline-first

**Qual biblioteca de armazenamento local, e por quê?** Hive, pelo pacote `hive_ce`, que é a versão mantida pela comunidade. Eu precisava guardar dois tipos de dado pequenos: o último saldo lido de cada conta (com o vetor) e a fila de operações pendentes. O Hive guarda mapas sem gerar código nem definir esquema, e funciona igual no Android, no Linux e na web, onde usa IndexedDB. Isso me deixou testar o modo offline no Chrome. Considerei o `sqflite`, que não roda na web, e o Drift, que exige definir tabelas e gerar código, o que é demais para uma fila. O `shared_preferences` eu já usava para o token, mas ele não serve para uma lista de operações que muda o tempo todo.

**O que apareceu na tela quando a sincronização foi recusada?** Com o app sem conexão, fiz um depósito de R$50, e o saldo provisório foi para R$630. Antes de reconectar, saquei R$200 da mesma conta direto na agência, com curl. Quando a conexão voltou, o app tentou sincronizar e recebeu 409. Apareceu um cartão vermelho "Conflito de sincronização" dizendo que o depósito de R$50 não foi aplicado, com o saldo real (R$380) e os botões "Descartar" e "Aplicar mesmo assim". A fila pausa até a decisão, porque as operações seguintes foram feitas sobre o mesmo saldo errado. Cliquei em "Aplicar mesmo assim" e o saldo foi para R$430. O print está em `evidencias/sprint3/app-conflito.png`.

Para os testes no Chrome, simulei a perda de rede com um proxy entre o app e as agências. Desligar o proxy corta a conexão do app sem derrubar as agências, que perderiam as contas por guardarem tudo em memória.

**Que risco a UI otimista traz para um app bancário, e como o design reduz esse risco?** A pessoa vê um saldo que ainda não existe e pode tomar decisões com base nele, como contar com um depósito que depois é recusado. Para reduzir isso:
- O saldo provisório tem a etiqueta "Provisório", e logo abaixo aparece o valor confirmado pela agência.
- Cada operação pendente aparece numa lista própria.
- Um saque offline só é aceito se couber no saldo provisório.
- Transferência sem conexão é recusada, porque o backend não sincroniza transferências.
- Um conflito nunca é resolvido sozinho.

## Funcionalidade adicional: histórico de líderes no app

**O que é:** o painel de liderança guarda as últimas 10 trocas de líder que o app viu, com a hora de cada uma, num item expansível "Histórico de líderes". A lista é montada pelas próprias consultas a `/bully/lider`: cada vez que a líder informada muda, o app registra a nova líder e a hora.

**Por que escolhi essa:** o painel só mostra o estado atual, e uma troca rápida de líder pode passar despercebida entre duas olhadas na tela. Com o histórico, dá para conferir no app a mesma sequência que o `historico_lideranca.py` monta a partir dos logs. No teste, o app mostrou 2 → 1 → 2 → 1 → 2, a mesma ordem dos logs.

**Evidência:** `evidencias/sprint3/funcionalidade-adicional.png`.

## Uso de IA

Usei o Claude (Anthropic) como apoio na implementação e na revisão do código e destes textos, conforme a nota de transparência do roteiro. Executei e validei os testes descritos acima e sou capaz de explicar cada trecho entregue.

No Sprint 3, usei o Claude Code para trocar o `request.app.state` por um serviço com lock, implementar o Bully, o heartbeat, o endpoint de sincronização e o app Flutter, e para rodar os testes e capturar os prints. Revisei o código e os resultados dos testes.
