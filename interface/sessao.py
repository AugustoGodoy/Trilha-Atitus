"""Contexto da aplicação e transições de estado (abrir/fechar caderno) compartilhadas pelas telas."""
import copy
from dataclasses import dataclass

import streamlit as st

from estudo_guiado.banco import Banco
from estudo_guiado.jornada import Servico

S = st.session_state


@dataclass
class Contexto:
    svc: Servico
    banco: Banco

    @property
    def cfg(self) -> dict:
        return self.svc.cfg

    @property
    def uid(self) -> int:
        return S.usuario["id"]


def abrir_caderno(ctx: Contexto, caderno_id: int) -> bool:
    """Carrega o caderno do usuário (conteúdo vem do cache, chat e notas vêm do banco). Sem chamadas ao LLM."""
    caderno = ctx.banco.caderno(ctx.uid, caderno_id)
    jornada = ctx.svc.abrir(caderno["hash"]) if caderno else None
    if not jornada:
        st.error("Não encontrei o conteúdo deste caderno. Envie o material novamente.")
        return False
    total = ctx.cfg["limites"]["perguntas_chat"]
    S.caderno, S.jornada, S.view = caderno, jornada, "chat"
    S.mapa = copy.deepcopy(jornada.conteudo["mapa"])
    S.corrigido, S.rodada_quiz = None, S.get("rodada_quiz", 0) + 1
    S.chat = ctx.banco.listar_mensagens(caderno_id)
    S.restantes = max(0, total - ctx.banco.perguntas_consumidas(caderno_id))
    return True


def fechar_caderno() -> None:
    for chave in ("caderno", "jornada", "view", "mapa", "corrigido", "chat", "restantes"):
        S.pop(chave, None)


def sair(ctx: Contexto) -> None:
    if token := S.get("token"):
        ctx.banco.encerrar_sessao(token)
    st.query_params.clear()
    S.clear()
