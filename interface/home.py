"""Início: saudação personalizada, estatísticas do usuário, cadernos salvos e criação de novo caderno."""
from pathlib import Path

import streamlit as st

from estudo_guiado.jornada import LimiteExcedido

from . import estilo
from .estilo import e
from .sessao import Contexto, S, abrir_caderno

COLUNAS_CARTOES = 2


def pagina_home(ctx: Contexto) -> None:
    u = S.usuario
    stats = ctx.banco.estatisticas(ctx.uid)
    cadernos = ctx.banco.listar_cadernos(ctx.uid)

    st.markdown(
        f'<h1 class="saudacao">{e(estilo.saudacao_do_dia())}, <span class="grad">{e(estilo.primeiro_nome(u["nome"]))}</span></h1>'
        f'<p class="sub">{"Continue de onde parou ou crie um novo caderno a partir do material da aula." if cadernos else "Vamos começar? Envie o material da aula e eu preparo sua jornada de estudo."}</p>',
        unsafe_allow_html=True)
    st.write("")
    _estatisticas(stats)
    st.write("")

    col_cadernos, col_novo = st.columns([1.55, 1], gap="large")
    with col_cadernos:
        _cadernos(ctx, cadernos)
    with col_novo:
        _novo_caderno(ctx)


def _estatisticas(stats: dict) -> None:
    itens = [(stats["cadernos"], "cadernos"), (stats["quizzes"], "quizzes feitos"),
             (f"{stats['media']:.1f}" if stats["media"] is not None else "—", "nota média"),
             (stats["perguntas"], "perguntas ao tutor")]
    for col, (n, rotulo) in zip(st.columns(4), itens):
        col.markdown(f'<div class="stat"><div class="n grad">{e(n)}</div><div class="l">{e(rotulo)}</div></div>',
                     unsafe_allow_html=True)


def _cadernos(ctx: Contexto, cadernos: list[dict]) -> None:
    st.markdown(estilo.painel_titulo("Seus cadernos"), unsafe_allow_html=True)
    if not cadernos:
        st.markdown('<div class="vazio">Você ainda não tem cadernos.<br>Envie um PDF ou PPTX ao lado para criar o primeiro.</div>',
                    unsafe_allow_html=True)
        return
    for inicio in range(0, len(cadernos), COLUNAS_CARTOES):
        for col, c in zip(st.columns(COLUNAS_CARTOES), cadernos[inicio:inicio + COLUNAS_CARTOES]):
            with col:
                _cartao(ctx, c)


def _cartao(ctx: Contexto, c: dict) -> None:
    with st.container(key=f"cartao_{c['id']}"):
        nota = f" · melhor nota {c['melhor_nota']:.1f}" if c["melhor_nota"] is not None else ""
        st.markdown(
            f'<div style="font-weight:600;font-size:1.02rem;margin-bottom:.25rem;">{e(c["titulo"])}</div>'
            f'<div class="hero-meta" style="margin-bottom:.8rem;">{e(estilo.data_curta(c["criado_em"]))} · '
            f'{e(c["perguntas"])} perguntas{e(nota)}</div>', unsafe_allow_html=True)
        abrir, excluir = st.columns([4, 1])
        if abrir.button("Abrir", key=f"abrir_{c['id']}", icon=":material/arrow_forward:", width="stretch"):
            if abrir_caderno(ctx, c["id"]):
                st.rerun()
        with excluir.popover("", icon=":material/delete:", width="stretch"):
            st.caption("Excluir este caderno, o histórico de chat e as notas do quiz?")
            if st.button("Confirmar exclusão", key=f"del_{c['id']}", type="primary"):
                ctx.banco.excluir_caderno(ctx.uid, c["id"])
                st.rerun()


def _titulo_padrao(nomes: list[str]) -> str:
    base = Path(nomes[0]).stem.replace("_", " ").replace("-", " ").strip() or "Novo caderno"
    return base if len(nomes) == 1 else f"{base} e mais {len(nomes) - 1}"


def _novo_caderno(ctx: Contexto) -> None:
    lim = ctx.cfg["limites"]
    restantes = lim["jornadas_por_dia"] - ctx.banco.cadernos_criados_hoje(ctx.uid)
    with st.container(key="painel_novo"):
        st.markdown(estilo.painel_titulo("Novo caderno"), unsafe_allow_html=True)
        st.caption(f"PDF ou PPTX com texto selecionável · até {lim['max_paginas_por_jornada']} páginas/slides no total "
                   f"e {lim['max_tamanho_arquivo_mb']} MB por arquivo.")
        arquivos = st.file_uploader("Slides ou PDFs", type=["pdf", "pptx"], accept_multiple_files=True,
                                    label_visibility="collapsed", key=f"upload_{S.get('rodada_upload', 0)}")
        titulo = st.text_input("Nome do caderno (opcional)", max_chars=80, placeholder="Ex.: Aula 03 · Arquitetura de produto")
        if st.button("Criar caderno", type="primary", width="stretch", icon=":material/auto_awesome:", disabled=not arquivos):
            _criar(ctx, arquivos, titulo)
        modo = ctx.svc.modo if ctx.svc.usar_api else "offline (sem chave de API: geração extrativa, sem custo)"
        st.markdown(f'<p class="aviso" style="text-align:left;">Modo de geração: <b>{e(modo)}</b> · '
                    f'{e(max(restantes, 0))} caderno(s) novo(s) disponíveis hoje</p>', unsafe_allow_html=True)


def _criar(ctx: Contexto, arquivos, titulo: str) -> None:
    pares = [(a.name, a.getvalue()) for a in arquivos]
    try:
        with st.spinner("Lendo o material e preparando sua jornada..."):
            jornada = ctx.svc.preparar(pares, jornadas_hoje=ctx.banco.cadernos_criados_hoje(ctx.uid))
    except LimiteExcedido as erro:
        st.error(str(erro))
        return
    except Exception as erro:
        st.error(f"Não foi possível processar o material: {erro}")
        return
    caderno_id = ctx.banco.registrar_caderno(ctx.uid, jornada.hash, " ".join(titulo.split()) or _titulo_padrao([n for n, _ in pares]))
    S.rodada_upload = S.get("rodada_upload", 0) + 1
    if abrir_caderno(ctx, caderno_id):
        S.reaproveitado = jornada.do_cache
        st.rerun()
