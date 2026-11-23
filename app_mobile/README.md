# app_mobile

App Flutter do ICEIBank (Sprint 3). Usa a mesma API das agências que o frontend web.

- Login JWT, saldo, depósito, saque e transferência.
- Painel com a líder atual, consultado a cada 3 s, com histórico das trocas.
- Modo offline: saldo em cache (Hive), fila de depósitos e saques pendentes e sincronização automática por `POST /contas/{id}/sincronizar`. Um conflito (409) aparece na tela com o saldo real.

Variáveis de build:

- `AGENCIA_HOST`: endereço das agências. Padrão `localhost`; no emulador Android, `10.0.2.2`.
- `PORTA_BASE`: porta da agência 0. Padrão `4071`.

```
flutter run -d chrome
flutter run --dart-define=AGENCIA_HOST=10.0.2.2
```
