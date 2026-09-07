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

_A preencher ao concluir a Parte E._

## Parte F — Autenticação JWT

_A preencher ao concluir a Parte F._

## Parte G — Frontend

_A preencher ao concluir a Parte G._

## Funcionalidade adicional

_A preencher junto do commit da funcionalidade adicional._
