"""Ponto de entrada da API Trilha Atitus."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import registrar_handlers
from .routes import cadernos, configuracao, estatisticas, sessoes, usuarios

app = FastAPI(
    title="Trilha Atitus API",
    description="Plataforma de estudo guiado com tutor inteligente",
    version="2.0.0",
)

_origens = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8765",
]
# Em produção: CORS_ORIGINS=https://trilha-web.up.railway.app,https://outro.dominio
_origens += [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registrar_handlers(app)

app.include_router(usuarios.router)
app.include_router(sessoes.router)
app.include_router(configuracao.router)
app.include_router(estatisticas.router)
app.include_router(cadernos.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/openapi.json", include_in_schema=False)
def openapi_alias():
    return app.openapi()
