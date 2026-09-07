# Respostas — Sprint 1

## Parte B — Relógio de Lamport

**Por que `max(local, recebido) + 1` e não adotar o recebido diretamente?** Porque o relógio precisa refletir *todo* o histórico causal que o processo já viu, não só a mensagem mais recente. Se eu simplesmente adotasse o valor recebido, um evento local que já aconteceu antes de eu receber a mensagem (e que tem um timestamp maior que o recebido) passaria a ter timestamp maior que um evento que veio depois dele causalmente — quebrando a garantia de que causa vem antes de efeito. O `+1` garante que o evento de recepção seja estritamente posterior a ambos: ao que eu já tinha visto e à mensagem que acabei de receber.

**Agência 0 no contador 10 recebe timestamp 3 — qual o novo valor?** `max(10, 3) + 1 = 11`. O contador da agência mais rápida não recua nunca — ela ignora timestamps atrasados na prática (o `max` os torna irrelevantes) e segue avançando a partir de si mesma. Implicação: uma agência que processa muitos eventos rapidamente "puxa" o relógio lógico do sistema para frente; uma agência lenta que manda uma mensagem atrasada não consegue arrastar as outras para trás — o relógio de Lamport é monotônico por construção, nunca diminui.

## Parte D — Transferências

_A preencher ao concluir a Parte D._

## Parte E — Linha do tempo

_A preencher ao concluir a Parte E._

## Parte F — Autenticação JWT

_A preencher ao concluir a Parte F._

## Parte G — Frontend

_A preencher ao concluir a Parte G._

## Funcionalidade adicional

_A preencher junto do commit da funcionalidade adicional._
