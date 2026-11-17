"""Erros padronizados no formato { error: { code, message, details, traceId } }."""
from __future__ import annotations

import traceback
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from estudo_guiado.banco import ErroAutenticacao
from estudo_guiado.jornada import LimiteExcedido
from estudo_guiado.llm import ErroLLM


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: list[dict] | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)


def _payload(code: str, message: str, details: list[dict] | None = None, trace_id: str | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "traceId": trace_id or str(uuid.uuid4()),
        }
    }


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=_payload(exc.code, exc.message, exc.details))

    @app.exception_handler(ErroAutenticacao)
    async def _auth(request: Request, exc: ErroAutenticacao):
        msg = str(exc)
        status = 401 if "incorret" in msg.lower() or "bloquead" in msg.lower() or "tentativa" in msg.lower() else 400
        if "Já existe" in msg:
            status = 409
        return JSONResponse(status_code=status, content=_payload("AUTH_ERROR", msg))

    @app.exception_handler(LimiteExcedido)
    async def _limite(request: Request, exc: LimiteExcedido):
        return JSONResponse(status_code=400, content=_payload("LIMITE_EXCEDIDO", str(exc)))

    @app.exception_handler(ErroLLM)
    async def _llm(request: Request, exc: ErroLLM):
        return JSONResponse(status_code=502, content=_payload("LLM_ERROR", str(exc)))

    @app.exception_handler(Exception)
    async def _gen(request: Request, exc: Exception):
        tid = str(uuid.uuid4())
        traceback.print_exc()
        return JSONResponse(status_code=500, content=_payload("INTERNAL_ERROR", "Erro inesperado no servidor.", trace_id=tid))
