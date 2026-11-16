"""Tela do caderno: conversa com o tutor no centro e Estúdio (resumo, mapa mental, quiz) à direita."""
import streamlit as st

from estudo_guiado import geracao

from . import estilo
from .estilo import e
from .sessao import Contexto, S, fechar_caderno

VISOES = [("chat", "Dúvidas", ":material/forum:"), ("resumo", "Resumo", ":material/summarize:"),
          ("mapa", "Mapa mental", ":material/account_tree:"), ("quiz", "Quiz", ":material/quiz:")]


def resumo_das_fontes(jornada) -> dict[str, int]:
    """Arquivo -> número de páginas/slides com texto."""
    paginas: dict[str, set[int]] = {}
    for t in jornada.trechos:
        paginas.setdefault(t.arquivo, set()).add(t.pagina)
    return {arq: len(pgs) for arq, pgs in paginas.items()}


def pagina_caderno(ctx: Contexto) -> None:
    centro, estudio = st.columns([2.2, 1], gap="medium")
    with centro, st.container(key="painel_centro"):
        _cabecalho(ctx)
        if S.pop("reaproveitado", False):
            st.success("Material já processado antes: conteúdo reaproveitado do cache, sem novas chamadas ao modelo.", icon="♻️")
        {"chat": _chat, "resumo": _resumo, "mapa": _mapa, "quiz": _quiz}[S.view](ctx)
    with estudio, st.container(key="painel_studio"):
        _estudio(ctx)


# ------------------------------------------------------------------ cabeçalho / estúdio

def _cabecalho(ctx: Contexto) -> None:
    cad = S.caderno
    fontes = resumo_das_fontes(S.jornada)
    if st.button("Voltar ao menu principal", icon=":material/arrow_back:", key="voltar_menu"):
        fechar_caderno()
        st.rerun()
    col_titulo, col_acoes = st.columns([6, 1])
    col_titulo.markdown(
        f'<div class="hero-icone"><img src="data:image/png;base64,{estilo.icone_b64()}" alt=""></div>'
        f'<h1 class="hero-titulo">{e(cad["titulo"])}</h1>'
        f'<div class="hero-meta">{e(len(fontes))} fonte(s) · {e(sum(fontes.values()))} páginas/slides · '
        f'criado em {e(estilo.data_curta(cad["criado_em"]))}</div>', unsafe_allow_html=True)
    with col_acoes.popover("", icon=":material/edit:", width="stretch"):
        novo = st.text_input("Renomear caderno", value=cad["titulo"], max_chars=80)
        if st.button("Salvar nome", type="primary"):
            ctx.banco.renomear_caderno(ctx.uid, cad["id"], novo)
            S.caderno = ctx.banco.caderno(ctx.uid, cad["id"])
            st.rerun()
    st.write("")


def _estudio(ctx: Contexto) -> None:
    st.markdown(estilo.painel_titulo("Estúdio"), unsafe_allow_html=True)
    for chave, rotulo, icone in VISOES:
        ativo = S.view == chave
        if st.button(rotulo, key=f"estudio_{chave}", icon=icone, width="stretch",
                     type="primary" if ativo else "secondary"):
            S.view = chave
            st.rerun()

    total = ctx.cfg["limites"]["perguntas_chat"]
    st.markdown(estilo.rotulo_secao("Seu progresso"), unsafe_allow_html=True)
    st.caption(f"Perguntas restantes: **{S.restantes} de {total}**")
    st.progress(S.restantes / total if total else 0.0)
    resultados = ctx.banco.resultados_quiz(S.caderno["id"])
    if resultados:
        ultima = resultados[0]
        st.markdown(estilo.chip(f"Última nota {ultima['nota']:.1f}/10") +
                    estilo.chip(f"Melhor {max(r['nota'] for r in resultados):.1f}", neutro=True) +
                    estilo.chip(f"{len(resultados)} tentativa(s)", neutro=True), unsafe_allow_html=True)
    else:
        st.caption("Você ainda não fez o quiz deste caderno.")
    with st.expander("Custo estimado do caderno"):
        uso = ctx.svc.custos(S.jornada.hash)
        if uso:
            st.table(uso)
        st.write(f"Total: R$ {sum(u['custo_brl'] for u in uso):.4f}")


# ------------------------------------------------------------------ conversa

def _chat(ctx: Contexto) -> None:
    j, c = S.jornada, S.jornada.conteudo
    nome = estilo.primeiro_nome(S.usuario["nome"])
    fontes = resumo_das_fontes(j)
    st.markdown(
        f'<div class="guia">Olá, <b>{e(nome)}</b>! Li <b>{len(fontes)}</b> fonte(s) e preparei o resumo, o mapa mental e o quiz '
        f'no <b>Estúdio</b>. Pergunte o que ficou confuso: respondo só com base no seu material, sempre citando o arquivo e a página.</div>',
        unsafe_allow_html=True)
    st.write("")

    for m in S.chat:
        with st.chat_message("user", avatar=":material/person:"):
            st.write(m["pergunta"])
        with st.chat_message("assistant", avatar=str(estilo.ICONE)):
            st.write(m["resposta"])
            if m["fontes"]:
                st.markdown("".join(estilo.citacao_html(f) for f in m["fontes"]), unsafe_allow_html=True)

    pergunta = None
    sugestoes = _sugestoes(ctx) if not S.chat and S.restantes > 0 else []
    if sugestoes:
        st.caption("Sugestões para começar")
        for i, sugestao in enumerate(sugestoes):
            if st.button(sugestao, key=f"sug_{i}"):
                pergunta = sugestao
    if S.restantes <= 0:
        st.success("Você usou todas as perguntas deste caderno. Bons estudos!", icon="🎉")
    entrada = st.chat_input("Pergunte sobre um conceito do material (resumo, mapa e quiz ficam no Estúdio)", disabled=S.restantes <= 0)
    if pergunta := pergunta or entrada:
        _perguntar(ctx, pergunta)


def _sugestoes(ctx: Contexto, maximo: int = 3) -> list[str]:
    """Perguntas baseadas nos termos-chave, só as que a recuperação consegue responder (evita sugerir algo recusado)."""
    minimo = ctx.cfg["chunking"]["score_minimo"]
    candidatas = (f"O que é {t['termo']}?" for t in S.jornada.conteudo["resumo"]["termos"])
    aprovadas = [q for q in candidatas if (achados := S.jornada.indice.buscar(q, 1)) and achados[0][1] >= minimo]
    return aprovadas[:maximo]


def _perguntar(ctx: Contexto, pergunta: str) -> None:
    with st.spinner("Buscando no material..."):
        r = ctx.svc.perguntar(S.jornada, pergunta)
    consumiu = not r["sem_base"] or ctx.cfg["limites"]["recusa_consome_pergunta"]
    ctx.banco.salvar_mensagem(S.caderno["id"], pergunta, r, consumiu)
    S.chat.append({"pergunta": pergunta, "resposta": r["resposta"], "fontes": r["fontes"], "sem_base": r["sem_base"]})
    if consumiu:
        S.restantes -= 1
    st.rerun()


# ------------------------------------------------------------------ resumo

def _resumo(ctx: Contexto) -> None:
    resumo = S.jornada.conteudo["resumo"]
    st.markdown(estilo.painel_titulo("Resumo por tópicos"), unsafe_allow_html=True)
    termos = [t["termo"] for t in resumo["termos"]]
    for tp in resumo["topicos"]:
        st.markdown(f'<div class="topico"><div class="t">{e(tp["titulo"])}</div>'
                    f'<div>{estilo.negrito_html(geracao.destacar_termos(tp["texto"], termos))}</div>'
                    f'<div style="margin-top:.5rem;">{estilo.citacao_html(tp["fonte"])}</div></div>', unsafe_allow_html=True)
    st.markdown(estilo.painel_titulo("Termos-chave para memorizar"), unsafe_allow_html=True)
    st.markdown("".join(f'<div class="termo"><b>{e(t["termo"])}</b><span>{e(t["definicao"])}</span></div>'
                        for t in resumo["termos"]), unsafe_allow_html=True)


# ------------------------------------------------------------------ mapa mental

def _dot(mapa: dict) -> str:
    def esc(s: str) -> str:
        return str(s).replace("\\", "").replace('"', "'")
    linhas = ['digraph G { bgcolor="transparent"; rankdir=LR; pad=0.2; nodesep=0.2; ranksep=0.9;',
              'node [shape=box, style="rounded,filled", fillcolor="#172033", color="#22d3ee", fontcolor="#e6e9ef", '
              'fontname="Helvetica", penwidth=1.3, margin="0.18,0.1"];',
              'edge [color="#4b5873", fontcolor="#8b93a7", fontname="Helvetica", fontsize=9, arrowsize=0.7];']
    linhas += [f'"{esc(n["id"])}" [label="{esc(n["rotulo"])}\\n(p. {n["fonte"]["pagina"]})"];' for n in mapa["nos"]]
    linhas += [f'"{esc(r["de"])}" -> "{esc(r["para"])}" [{_atributos_aresta(r["tipo"], esc)}];' for r in mapa["relacoes"]]
    return "\n".join(linhas) + "}"


def _atributos_aresta(tipo: str, esc) -> str:
    """Relações laterais ("relaciona-se") não definem hierarquia: ficam tracejadas, sem rótulo e sem esticar o layout."""
    if str(tipo).lower().startswith("relaciona"):
        return "style=dashed, constraint=false, arrowhead=none"
    return f'label="{esc(tipo)}"'


def _trecho_da_fonte(f: dict) -> str:
    return "\n\n".join(t.texto for t in S.jornada.trechos if t.arquivo == f["arquivo"] and t.pagina == f["pagina"])


def _mapa(ctx: Contexto) -> None:
    mapa = S.mapa
    st.markdown(estilo.painel_titulo("Mapa mental"), unsafe_allow_html=True)
    st.graphviz_chart(_dot(mapa), width="stretch")

    por_id = {n["id"]: n for n in mapa["nos"]}
    if por_id:
        sel = st.selectbox("Ver o trecho de um nó", list(por_id), format_func=lambda i: por_id[i]["rotulo"])
        f = por_id[sel]["fonte"]
        st.markdown(estilo.citacao_html(f), unsafe_allow_html=True)
        st.text(_trecho_da_fonte(f)[:1200])
        for p in S.jornada.conteudo["imagens"].get(f"{f['arquivo']}|{f['pagina']}", [])[:2]:
            st.image(p, width=260)

    with st.expander("Editar mapa (adicionar/remover nós)"):
        _editor_mapa(mapa, por_id)


def _editor_mapa(mapa: dict, por_id: dict) -> None:
    col1, col2 = st.columns(2)
    with col1:
        rotulo = st.text_input("Novo nó")
        pai = st.selectbox("Ligar a", list(por_id), format_func=lambda i: por_id[i]["rotulo"], key="pai") if por_id else None
        if st.button("Adicionar") and rotulo.strip():
            novo = f"u{len(mapa['nos']) + 1}_{abs(hash(rotulo)) % 9999}"
            fonte = por_id[pai]["fonte"] if pai else S.jornada.trechos[0].fonte()
            mapa["nos"].append({"id": novo, "rotulo": rotulo.strip(), "fonte": fonte})
            if pai:
                mapa["relacoes"].append({"de": pai, "para": novo, "tipo": "relaciona-se"})
            st.rerun()
    with col2:
        rem = st.selectbox("Remover nó", list(por_id), format_func=lambda i: por_id[i]["rotulo"], key="rem") if por_id else None
        if st.button("Remover") and rem:
            mapa["nos"] = [n for n in mapa["nos"] if n["id"] != rem]
            mapa["relacoes"] = [r for r in mapa["relacoes"] if rem not in (r["de"], r["para"])]
            st.rerun()


# ------------------------------------------------------------------ quiz

def _quiz(ctx: Contexto) -> None:
    quiz = S.jornada.conteudo["quiz"]
    st.markdown(estilo.painel_titulo("Quiz"), unsafe_allow_html=True)
    if not quiz["questoes"]:
        st.warning("Não foi possível gerar questões com este material (conteúdo insuficiente).")
        return
    prefixo = f"q{S.caderno['id']}_{S.rodada_quiz}"
    respostas: dict[int, str] = {}
    with st.form(f"form_{prefixo}", border=False):
        for i, q in enumerate(quiz["questoes"]):
            st.markdown(f'**{i + 1}.** {e(q["enunciado"])} <span class="nivel">{e(q["nivel"])}</span>', unsafe_allow_html=True)
            respostas[i] = st.radio("Alternativas", list("ABCD"), index=None, key=f"{prefixo}_{i}",
                                    format_func=lambda L, q=q: f"{L}) {q['alternativas']['ABCD'.index(L)]}",
                                    label_visibility="collapsed", disabled=S.corrigido is not None)
        enviado = st.form_submit_button("Corrigir", type="primary", disabled=S.corrigido is not None)
    if enviado:
        S.corrigido = geracao.corrigir_quiz(quiz, respostas)
        ctx.banco.salvar_resultado_quiz(S.caderno["id"], S.corrigido["nota"], S.corrigido["acertos"], S.corrigido["total"])
        st.rerun()
    if S.corrigido:
        _resultado_quiz(S.corrigido)


def _resultado_quiz(r: dict) -> None:
    st.metric("Nota", f"{r['nota']}/10", f"{r['acertos']} de {r['total']} acertos")
    for it in r["itens"]:
        if not it["acertou"]:
            with st.container(border=True):
                st.markdown(f"**Questão {it['indice'] + 1}**: você marcou {it['marcada'] or '—'}; gabarito {it['gabarito']}.")
                st.write(it["justificativa"])
                st.markdown(estilo.citacao_html(it["fonte"]), unsafe_allow_html=True)
    if st.button("Refazer quiz", icon=":material/refresh:"):
        S.corrigido, S.rodada_quiz = None, S.rodada_quiz + 1
        st.rerun()
