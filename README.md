# ICEIBank

Banco simplificado dividido em agências, projeto de 4 sprints. Sprint 1: API REST/MVC (FastAPI) + relógio lógico de Lamport + autenticação JWT + frontend (Vue.js).

Ver [`CONTEXT.md`](./CONTEXT.md) para o glossário do domínio e [`docs/adr/`](./docs/adr/) para as decisões de design registradas.

## Como rodar (Sprint 1)

Backend (repita em 3 terminais, um por agência):

```
cd agencia
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
AGENCIA_ID=0 python -m app.main   # troque para 1 e 2 nos outros terminais
```

Todas as agências devem compartilhar o mesmo segredo JWT: exporte `ICEIBANK_JWT_SECRET` antes de subir os 3 processos.

Criar uma conta exige um token de serviço (ver ADR 0002 e RESPOSTAS.md) — gere um com:

```
python mint_service_token.py
```

Frontend:

```
cd frontend
npm install
npm run dev
```
