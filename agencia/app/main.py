import os

from fastapi import FastAPI

from app import config
from app.routers import contas, transferencias
from app.services.event_log import RegistroEventos
from app.services.lamport_clock import RelogioLamport

id_agencia = int(os.getenv("AGENCIA_ID", "0"))
agencia_config = next((a for a in config.AGENCIAS if a["id"] == id_agencia), None)

if agencia_config is None:
    raise SystemExit(f"Agência {id_agencia} não configurada em config.py")

app = FastAPI(title=f"ICEIBank - Agência {id_agencia}")

app.state.id_agencia = id_agencia
app.state.relogio = RelogioLamport()
app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
app.state.contas = {}

app.include_router(contas.router)
app.include_router(transferencias.router)

if __name__ == "__main__":
    import uvicorn

    porta = int(agencia_config["url"].rsplit(":", 1)[1])
    uvicorn.run(app, host="0.0.0.0", port=porta)
