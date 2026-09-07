# ICEIBank — Domain Context

Glossary only — no implementation details. This project runs across 4 sprints on one evolving codebase; terms below are Sprint 1 (REST/MVC + Lamport clock). Terms still under discussion are marked `(EM ABERTO)` and left out until resolved.

## Core entities

**Agência** — an independent REST service process. Same code deployed 3 times, distinguished only by `AGENCIA_ID` (0, 1, 2). Owns a partition of Contas (not a replica of the whole bank) and holds its own `RelogioLamport` (local logical clock) and event log. Agências never share memory or a database — the only way one learns about another's state is by receiving a message from it.

**Conta** — belongs to exactly one Agência, decided by `id_conta % 3`. Fields: `id`, `nomeAluno`, `saldo`. Held in-memory only (no persistence this sprint — restart empties it).

**Partição** — the assignment rule (`id_conta % número_de_agências`) that gives each Conta exactly one owning Agência. Distinguished deliberately from *replication*: no Agência ever holds a second copy of another's Contas.

**RelogioLamport** — a per-Agência integer counter, not a wall clock. Three operations: `eventoLocal()` (increments before any local event), `aoEnviar()` (increments and stamps an outgoing message), `aoReceber(t)` (sets counter to `max(local, t) + 1`). Guarantees: if A causally happened-before B, `timestamp(A) < timestamp(B)`. Does **not** guarantee the converse — equal or out-of-order timestamps may be genuinely concurrent events, not causally related ones. This gap is what motivates the vector clock in Sprint 2.

**Evento** — an immutable record of one thing an Agência did (`CRIAR_CONTA`, `DEPOSITO`, `SAQUE`, `TRANSFERENCIA_DEBITO`, `TRANSFERENCIA_CREDITO`, `TRANSFERENCIA_CREDITO_REMOTO`, `TRANSFERENCIA_FALHOU`). Carries `timestampLamport` (the logical clock, authoritative for ordering) and `horaParede` (wall clock, informational only — never used for a system decision). Appended to a per-Agência `.jsonl` log, never mutated.

**Transferência Local** — debit and credit both happen inside the same Agência's process. No message crosses a process boundary, so it uses `eventoLocal()` only — `aoEnviar()`/`aoReceber()` don't apply because there's no send/receive to mark.

**Transferência Entre Agências** — debit happens locally (`eventoLocal()`) in the origin Agência, then a REST call carries the Lamport timestamp to the destination Agência via `aoEnviar()` (origin) / `aoReceber()` (destination). This is the one path in Sprint 1 where two Agências' clocks actually interact.

**Falha Conhecida (inconsistência conhecida)** — if the destination Agência is unreachable mid-transfer, the already-applied debit is *not* rolled back. This is a deliberate, in-scope state for Sprint 1, not a bug to fix — it's the exact gap Sprint 4 closes with 2PC/Saga. The system's only obligation this sprint is to record it (`TRANSFERENCIA_FALHOU`), not repair it.

**Linha do Tempo Unificada** — an offline merge of all Agências' `.jsonl` logs, sorted by `timestampLamport`. Its purpose is observational: surfacing timestamp ties across Agências as candidate-concurrent events (see RelogioLamport's converse gap above).

## Identity and trust

**Conta (as principal)** — the Conta entity doubles as the JWT login identity: it gains a `senha` field, and logging in as `id_conta` + `senha` is authenticating *as that Conta*, not as some separate person who happens to own it. Authentication as a Conta only authorizes operating on that same Conta — a valid token for Conta 3 saldo/depositar/sacar/transferir on Conta 7 is a 403, not a 200. There is no "Cliente" or "Usuário" entity in this domain — see *Terms deliberately avoided* below and [[0001]].

**Credencial de Serviço** — the trust mechanism for Agência-to-Agência calls (`creditar-remoto`). A shared secret known to all three Agência processes, checked via a header, distinct from a Conta's JWT. It authenticates "this call came from a peer Agência," not "this call came from a specific Conta" — deliberately not the same trust concept as user auth. See [[0002]].

## Terms deliberately avoided

**Cliente / Usuário** — considered and rejected as a separate entity from Conta for Sprint 1. Introducing it would require a directory mapping people to Contas that spans Agências — state that doesn't exist anywhere in this architecture (no DB, no shared memory, partition-only). Revisit if a later sprint introduces shared/persistent storage (Sprint 4, containers) — until then, "the Conta is the identity" is the deliberate model, not an oversight.

## Sprint boundary notes (for future-you, not implementation)

- No database exists yet — Contas live in a process-local dict. Sprint 4 introduces containers, which is the natural point persistence would show up. Don't let Sprint 1 identity modeling assume a shared user directory across Agências; none exists until then.
- Only a scalar Lamport clock exists. Sprint 2 introduces the vector clock specifically to resolve the "equal timestamp ≠ definitely concurrent" gap noted above — don't reach for anything vector-clock-shaped this sprint.
- Agência-to-agência communication is synchronous REST today. Sprint 2 introduces Pub-Sub; the `TRANSFERENCIA_ENTRE_AGENCIAS` path is the one most likely to be rebuilt on top of messaging then, so avoid coupling its internals too tightly to "it's an HTTP call" assumptions elsewhere in the code.
