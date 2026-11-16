"""Tela de login / criação de conta."""
import streamlit as st

from estudo_guiado.banco import Banco, ErroAutenticacao

from . import estilo


def _entrar(banco: Banco, usuario: dict) -> None:
    token = banco.criar_sessao(usuario["id"])
    st.session_state.usuario = usuario
    st.session_state.token = token
    st.query_params["s"] = token
    st.rerun()


def tela_login(banco: Banco) -> None:
    estilo.aplicar(login=True)
    _, centro, _ = st.columns([1, 1.15, 1])
    with centro:
        st.markdown(estilo.logo_html(58, centralizada=True), unsafe_allow_html=True)
        with st.container(key="painel_login"):
            st.markdown(
                '<h2 style="text-align:center;margin:.2rem 0 0 0;white-space:nowrap;">Estudo <span class="grad">Guiado</span></h2>'
                '<p class="sub" style="text-align:center;margin-bottom:1.1rem;">Seu tutor inteligente para transformar '
                'material de aula em estudo.</p>', unsafe_allow_html=True)
            aba_entrar, aba_criar = st.tabs(["Entrar", "Criar conta"])
            with aba_entrar:
                _form_entrar(banco)
            with aba_criar:
                _form_criar(banco)
        st.markdown(f'<p class="aviso">{estilo.AVISO_FERRAMENTA_DE_APOIO}<br>Seus cadernos e histórico ficam salvos na sua conta.</p>',
                    unsafe_allow_html=True)


def _form_entrar(banco: Banco) -> None:
    with st.form("form_entrar"):
        email = st.text_input("E-mail", placeholder="voce@atitus.edu.br", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
        enviado = st.form_submit_button("Entrar", type="primary", width="stretch")
    if enviado:
        try:
            _entrar(banco, banco.autenticar(email, senha))
        except ErroAutenticacao as erro:
            st.error(str(erro))


def _form_criar(banco: Banco) -> None:
    with st.form("form_criar"):
        nome = st.text_input("Nome completo", key="cad_nome")
        email = st.text_input("E-mail", placeholder="voce@atitus.edu.br", key="cad_email")
        col1, col2 = st.columns(2)
        senha = col1.text_input("Senha", type="password", key="cad_senha", help="Mínimo de 8 caracteres, com letras e números.")
        confirmar = col2.text_input("Confirmar senha", type="password", key="cad_confirmar")
        enviado = st.form_submit_button("Criar conta e entrar", type="primary", width="stretch")
    if enviado:
        if senha != confirmar:
            st.error("As senhas não coincidem.")
            return
        try:
            _entrar(banco, banco.criar_usuario(nome, email, senha))
        except ErroAutenticacao as erro:
            st.error(str(erro))
