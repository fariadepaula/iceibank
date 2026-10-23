# Chamadas Agência-a-Agência usam uma credencial de serviço própria, não o JWT de quem chamou

`creditar-remoto` modifica uma Conta, então pela nossa própria regra toda rota assim precisa de um token válido. Reenviar o JWT de quem chamou acoplaria uma chamada interna de sistema ao ciclo de vida daquela sessão (expiração, revogação) sem necessidade, e confundiria "esta requisição veio de uma pessoa autenticada" com "esta requisição veio de uma Agência parceira confiável", que são afirmações diferentes.

Usamos em vez disso um segredo compartilhado (variável de ambiente, verificado via cabeçalho da requisição) conhecido pelos três processos de Agência. É um mecanismo de confiança separado dos JWTs de usuário, não uma versão mais fraca dele: uma Agência parceira nunca está "logada" como uma Conta.

Consequência: se a comunicação entre Agências deixar de ser HTTP síncrono (Sprint 2, Pub-Sub), o transporte dessa credencial muda, mas a decisão de fundo (confiança entre pares é um conceito distinto de autenticação de usuário) deve continuar valendo.

## Atualização (Sprint 2)

A chamada `creditar-remoto` deixou de existir: o crédito entre agências chega por mensagem do RabbitMQ, consumida numa thread fora das rotas do FastAPI, sem cabeçalho HTTP onde levar um token. A confiança entre pares passou a ser a credencial do broker (a `RABBITMQ_URL`, com usuário e senha da instância), conhecida só pelas três agências. A decisão de fundo continua valendo: confiança entre agências é distinta da autenticação de uma Conta. O token de serviço segue em uso para `POST /contas`.
