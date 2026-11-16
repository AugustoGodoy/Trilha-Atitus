"""Trilha · Atitus: ponto de entrada (autenticação, barra lateral e roteamento entre telas)."""
import streamlit as st

from estudo_guiado.banco import Banco
from estudo_guiado.jornada import Servico
from interface import estilo
from interface.caderno import pagina_caderno, resumo_das_fontes
from interface.home import pagina_home
from interface.login import tela_login
from interface.sessao import Contexto, S, abrir_caderno, fechar_caderno, sair

st.set_page_config(page_title="Trilha · Atitus", page_icon=str(estilo.ICONE), layout="wide",
                   initial_sidebar_state="expanded")

LIMITE_CADERNOS_NA_BARRA = 15


@st.cache_resource
def contexto() -> Contexto:
    svc = Servico()
    return Contexto(svc, Banco(svc.cfg["banco"]["caminho"]))


def restaurar_sessao(ctx: Contexto) -> None:
    """Mantém o login ao recarregar a página, via token de sessão (só o hash fica no banco)."""
    if "usuario" in S or not (token := st.query_params.get("s")):
        return
    if usuario := ctx.banco.usuario_da_sessao(token):
        S.usuario, S.token = usuario, token
    else:
        st.query_params.clear()


def barra_lateral(ctx: Contexto) -> None:
    with st.sidebar:
        st.markdown(estilo.logo_html(40), unsafe_allow_html=True)
        if st.button("Novo caderno", icon=":material/add:", type="primary", width="stretch"):
            fechar_caderno()
            st.rerun()

        if "jornada" in S:
            st.markdown(estilo.rotulo_secao("Fontes"), unsafe_allow_html=True)
            for arquivo, paginas in resumo_das_fontes(S.jornada).items():
                tipo = arquivo.rsplit(".", 1)[-1].lower()
                st.markdown(f'<div class="fonte"><span class="tipo {e_tipo(tipo)}">{estilo.e(tipo.upper())}</span>'
                            f'<span class="nome" title="{estilo.e(arquivo)}">{estilo.e(arquivo)}</span>'
                            f'<span class="pg">{paginas} pág.</span></div>', unsafe_allow_html=True)

        cadernos = ctx.banco.listar_cadernos(ctx.uid)
        if cadernos:
            st.markdown(estilo.rotulo_secao("Meus cadernos"), unsafe_allow_html=True)
        for c in cadernos[:LIMITE_CADERNOS_NA_BARRA]:
            ativo = S.get("caderno", {}).get("id") == c["id"]
            if st.button(c["titulo"], key=f"nav_{c['id']}", icon=":material/description:", width="stretch",
                         type="primary" if ativo else "secondary") and not ativo:
                if abrir_caderno(ctx, c["id"]):
                    st.rerun()

        st.markdown(estilo.rotulo_secao("Conta"), unsafe_allow_html=True)
        st.markdown(estilo.cartao_usuario(S.usuario), unsafe_allow_html=True)
        if st.button("Sair", icon=":material/logout:", width="stretch"):
            sair(ctx)
            st.rerun()


def e_tipo(ext: str) -> str:
    return ext if ext in ("pdf", "pptx") else "pdf"


ctx = contexto()
restaurar_sessao(ctx)

if "usuario" not in S:
    tela_login(ctx.banco)
    st.stop()

estilo.aplicar()
barra_lateral(ctx)
if "caderno" in S and ctx.banco.caderno(ctx.uid, S.caderno["id"]) is None:
    fechar_caderno()
(pagina_caderno if "jornada" in S else pagina_home)(ctx)
st.markdown(f'<p class="aviso">{estilo.AVISO_FERRAMENTA_DE_APOIO}</p>', unsafe_allow_html=True)
