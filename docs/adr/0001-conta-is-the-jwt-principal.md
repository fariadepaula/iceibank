# A Conta is the JWT principal — there is no separate Cliente/Usuário entity

Sprint 1 has no database and no shared state between Agências — each one only ever knows about the Contas in its own partition. A "Cliente who can own several Contas across Agências" would need a directory spanning all three Agências, which nothing in this architecture provides yet. We chose instead to let the Conta itself be the login identity: it gains a `senha` field, and `id_conta` + `senha` *is* the credential.

Consequence: a Conta can only ever authenticate itself, never act on another Conta's behalf, and any future "one person, several accounts" feature needs a real shared identity store — which is a Sprint 4 (containers/persistence) concern, not a Sprint 1 one. Revisit this decision if that lands.
