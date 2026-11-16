"""Schemas Pydantic de request/response."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CriarUsuarioIn(BaseModel):
    nome: str
    email: str
    senha: str


class SessaoIn(BaseModel):
    email: str
    senha: str


class RenomearCadernoIn(BaseModel):
    titulo: str = Field(max_length=80)


class PerguntaIn(BaseModel):
    pergunta: str


class CorrecaoQuizIn(BaseModel):
    respostas: dict[int, str]


def ok(data: Any, meta: dict | None = None, links: dict | None = None) -> dict:
    out: dict[str, Any] = {"data": data}
    if meta is not None:
        out["meta"] = meta
    if links is not None:
        out["links"] = links
    return out
