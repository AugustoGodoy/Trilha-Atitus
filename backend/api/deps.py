"""Dependências compartilhadas: config, Banco, Servico e usuário autenticado."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header

from estudo_guiado.banco import Banco
from estudo_guiado.config import carregar_config
from estudo_guiado.jornada import Jornada, Servico

from .errors import ApiError


@lru_cache(maxsize=1)
def get_cfg() -> dict:
    return carregar_config()


@lru_cache(maxsize=1)
def get_svc() -> Servico:
    return Servico(get_cfg())


@lru_cache(maxsize=1)
def get_banco() -> Banco:
    return Banco(get_cfg()["banco"]["caminho"])


def usuario_atual(
    authorization: Annotated[str | None, Header()] = None,
    banco: Banco = Depends(get_banco),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "UNAUTHORIZED", "Informe Authorization: Bearer <token>.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise ApiError(401, "UNAUTHORIZED", "Token ausente.")
    usuario = banco.usuario_da_sessao(token)
    if not usuario:
        raise ApiError(401, "UNAUTHORIZED", "Sessão inválida ou expirada.")
    usuario["_token"] = token
    return usuario


def jornada_do_caderno(svc: Servico, banco: Banco, usuario: dict, caderno_id: int) -> tuple[dict, Jornada]:
    caderno = banco.caderno(usuario["id"], caderno_id)
    if not caderno:
        raise ApiError(404, "NOT_FOUND", "Caderno não encontrado.")
    jornada = svc.abrir(caderno["hash"])
    if not jornada:
        raise ApiError(404, "NOT_FOUND", "Não encontrei o conteúdo deste caderno. Envie o material novamente.")
    return caderno, jornada


def resumo_das_fontes(jornada: Jornada) -> dict[str, int]:
    paginas: dict[str, set[int]] = {}
    for t in jornada.trechos:
        paginas.setdefault(t.arquivo, set()).add(t.pagina)
    return {arq: len(pgs) for arq, pgs in paginas.items()}
