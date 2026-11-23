import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.dependencias import obter_agencia, obter_bully
from app.routers import auth, bully, contas, transferencias
from app.services.agencia import ErroNegocio
from app.services.mensageria import assinar

agencia = obter_agencia()
servico_bully = obter_bully()


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    # Consumidor: créditos vindos de outras agências chegam pela fila, não por HTTP
    assinar(agencia.id, agencia.aplicar_credito_remoto)
    # Ao subir, cada agência dispara a própria eleição para descobrir (ou
    # estabelecer) a líder; em thread para não atrasar o início do servidor.
    threading.Thread(target=servico_bully.iniciar_eleicao, daemon=True).start()
    servico_bully.iniciar_heartbeat()
    yield


app = FastAPI(title=f"ICEIBank - Agência {agencia.id}", lifespan=ciclo_de_vida)

# Projeto acadêmico local - em produção restrinja allow_origins ao domínio do frontend.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ErroNegocio)
def erro_de_negocio(_request: Request, erro: ErroNegocio):
    return JSONResponse(status_code=erro.status, content={"detail": erro.detalhe})


app.include_router(auth.router)
app.include_router(contas.router)
app.include_router(transferencias.router)
app.include_router(bully.router)

if __name__ == "__main__":
    import uvicorn

    porta = int(config.AGENCIAS[agencia.id]["url"].rsplit(":", 1)[1])
    uvicorn.run(app, host="0.0.0.0", port=porta)
