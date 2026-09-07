# A Conta é o principal do JWT, não existe um Cliente/Usuário separado

O Sprint 1 não tem banco de dados nem estado compartilhado entre Agências, cada uma só conhece as Contas da sua própria partição. Um "Cliente que pode ter várias Contas em Agências diferentes" precisaria de um diretório que atravessasse as três Agências, e nada nesta arquitetura fornece isso ainda. Optei por deixar a própria Conta ser a identidade de login: ela ganha um campo `senha`, e `id_conta` + `senha` é a credencial.

Consequência: uma Conta só consegue autenticar a si mesma, nunca agir em nome de outra Conta, e qualquer funcionalidade futura de "uma pessoa, várias contas" precisa de um diretório de identidade real, o que é assunto do Sprint 4 (containers/persistência), não do Sprint 1. Revisitar esta decisão se isso acontecer.
