import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import auth, contas, transferencias
from app.services.event_log import RegistroEventos
from app.services.vector_clock import RelogioVetorial

id_agencia = int(os.getenv("AGENCIA_ID", "0"))
agencia_config = next((a for a in config.AGENCIAS if a["id"] == id_agencia), None)

if agencia_config is None:
    raise SystemExit(f"Agência {id_agencia} não configurada em config.py")

app = FastAPI(title=f"ICEIBank - Agência {id_agencia}")

# Projeto acadêmico local - em produção restrinja allow_origins ao domínio do frontend.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.state.id_agencia = id_agencia
app.state.relogio = RelogioVetorial(id_agencia, config.NUMERO_AGENCIAS)
app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
app.state.contas = {}
app.state.operacoes_vistas = {}

app.include_router(auth.router)
app.include_router(contas.router)
app.include_router(transferencias.router)

if __name__ == "__main__":
    import uvicorn

    porta = int(agencia_config["url"].rsplit(":", 1)[1])
    uvicorn.run(app, host="0.0.0.0", port=porta)
