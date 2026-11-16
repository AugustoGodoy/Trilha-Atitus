"""Tema visual (escuro, com a marca da Atitus) e pequenos componentes HTML.

Todo texto vindo do usuário ou dos arquivos enviados passa por `html.escape` antes de entrar em HTML.
"""
import base64
import re
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO = ASSETS / "atitus_logo.png"
ICONE = ASSETS / "atitus_icone.png"

AVISO_FERRAMENTA_DE_APOIO = "Ferramenta de apoio ao estudo. Não substitui o professor nem o material oficial da disciplina."

CSS = """
:root{
  --bg:#0b0e14; --painel:#121722; --painel2:#171d2b; --borda:#232b3d; --borda2:#2d3850;
  --texto:#e6e9ef; --suave:#8b93a7; --ciano:#22d3ee; --indigo:#6366f1; --violeta:#a78bfa;
  --grad:linear-gradient(135deg,#22d3ee 0%,#6366f1 100%);
}
html, body, .stApp, [data-testid="stAppViewContainer"]{
  font-family: Inter, "Segoe UI", Roboto, "Helvetica Neue", system-ui, sans-serif;
  color:var(--texto);
}
.stApp{
  background:
    radial-gradient(1100px 560px at 88% -12%, rgba(34,211,238,.09), transparent 60%),
    radial-gradient(900px 520px at -8% 108%, rgba(99,102,241,.12), transparent 60%),
    var(--bg);
}
.stApp::before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:linear-gradient(rgba(255,255,255,.028) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.028) 1px,transparent 1px);
  background-size:44px 44px;
  -webkit-mask-image:radial-gradient(ellipse 80% 60% at 50% 0%, #000 0%, transparent 75%);
          mask-image:radial-gradient(ellipse 80% 60% at 50% 0%, #000 0%, transparent 75%);
}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer{display:none !important;}
.block-container{padding-top:2.2rem; padding-bottom:2rem; max-width:1480px;}
h1,h2,h3,h4{letter-spacing:-.01em; color:var(--texto);}
hr{border-color:var(--borda) !important;}
::-webkit-scrollbar{width:10px;height:10px} ::-webkit-scrollbar-thumb{background:#262f42;border-radius:8px}
::-webkit-scrollbar-thumb:hover{background:#34405a}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{background:#0e121a; border-right:1px solid var(--borda);}
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarUserContent"]{padding-top:1.2rem;}
/* menu lateral fixo: sempre visível, sem botão de recolher (nem recolhe sozinho em telas estreitas) */
[data-testid="stSidebar"]{transform:none !important; margin-left:0 !important; visibility:visible !important;
  min-width:300px !important; width:300px !important;}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"]{display:none !important;}
.rotulo-secao{font-size:.72rem; font-weight:600; letter-spacing:.12em; color:var(--suave);
  text-transform:uppercase; margin:1.1rem 0 .45rem .2rem;}
.logo-wrap{padding:.2rem .2rem .6rem .2rem;}
.logo-wrap img{height:44px; width:auto; display:block;}

/* ---------- botões ---------- */
[data-testid^="stBaseButton-secondary"], [data-testid^="stBaseButton-primary"], [data-testid="stBaseButton-tertiary"]{
  border-radius:14px; font-weight:500; transition:all .18s ease;
}
[data-testid^="stBaseButton-secondary"]{
  background:var(--painel2); color:var(--texto); border:1px solid var(--borda);
}
[data-testid^="stBaseButton-secondary"]:hover{
  border-color:var(--ciano); color:#fff; background:#1a2234; box-shadow:0 0 0 1px rgba(34,211,238,.25), 0 8px 24px rgba(34,211,238,.08);
}
[data-testid^="stBaseButton-primary"]{
  background:var(--grad); color:#04111a; border:0; font-weight:600; box-shadow:0 8px 24px rgba(34,211,238,.18);
}
[data-testid^="stBaseButton-primary"]:hover{filter:brightness(1.08); box-shadow:0 10px 30px rgba(99,102,241,.35); color:#04111a;}
[data-testid^="stBaseButton-primary"] p{color:#04111a !important;}
button:disabled{opacity:.45 !important;}

/* navegação lateral e cartões do estúdio: primário vira "selecionado" discreto */
[class*="st-key-nav_"] button, [class*="st-key-estudio_"] button, [class*="st-key-sug_"] button{
  justify-content:flex-start; text-align:left;
}
[class*="st-key-nav_"] button p{overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
[class*="st-key-nav_"] [data-testid^="stBaseButton-primary"],
[class*="st-key-estudio_"] [data-testid^="stBaseButton-primary"]{
  background:linear-gradient(135deg,rgba(34,211,238,.16),rgba(99,102,241,.16));
  border:1px solid rgba(34,211,238,.55); color:#fff; box-shadow:none;
}
[class*="st-key-nav_"] [data-testid^="stBaseButton-primary"] p,
[class*="st-key-estudio_"] [data-testid^="stBaseButton-primary"] p{color:#fff !important;}
[class*="st-key-estudio_"] button{min-height:3.5rem; border-radius:16px; padding:.5rem .9rem;}
[class*="st-key-sug_"] button{border-radius:999px; font-size:.88rem; color:var(--suave); background:transparent;
  border:1px solid var(--borda2);}
[class*="st-key-sug_"] button:hover{color:#fff;}

/* ---------- painéis ---------- */
[class*="st-key-painel"]{
  background:linear-gradient(180deg,rgba(23,29,43,.72),rgba(18,23,34,.9));
  border:1px solid var(--borda); border-radius:24px; padding:1.4rem 1.5rem;
  box-shadow:0 20px 60px rgba(0,0,0,.35);
  backdrop-filter:blur(6px);
}
.painel-titulo{font-size:1.02rem; font-weight:600; margin:0 0 .85rem 0; display:flex; align-items:center; gap:.5rem;}
.painel-titulo .ponto{width:8px;height:8px;border-radius:50%;background:var(--ciano);box-shadow:0 0 12px var(--ciano);}
[class*="st-key-cartao_"]{
  background:var(--painel); border:1px solid var(--borda); border-radius:20px; padding:1.1rem 1.2rem .9rem 1.2rem;
  transition:all .2s ease;
}
[class*="st-key-cartao_"]:hover{border-color:rgba(34,211,238,.5); transform:translateY(-2px);
  box-shadow:0 14px 40px rgba(34,211,238,.08);}
[data-testid="stExpander"] details{background:var(--painel2); border:1px solid var(--borda); border-radius:14px;}
[data-testid="stExpander"] summary{color:var(--suave);}
[data-testid="stForm"]{border:0; padding:0; background:transparent;}

/* ---------- textos / componentes ---------- */
.grad{background:linear-gradient(90deg,#22d3ee,#818cf8 55%,#c084fc); -webkit-background-clip:text;
  background-clip:text; color:transparent; -webkit-text-fill-color:transparent;}
.saudacao{font-size:2.7rem; font-weight:700; letter-spacing:-.025em; line-height:1.1; margin:0;}
.sub{color:var(--suave); font-size:1.02rem; margin:.5rem 0 0 0;}
.hero-icone{width:56px;height:56px;border-radius:16px;background:var(--grad);display:flex;align-items:center;
  justify-content:center;box-shadow:0 10px 30px rgba(34,211,238,.25);margin-bottom:1rem;}
.hero-icone img{width:30px;height:30px;filter:brightness(0.08);}
.hero-titulo{font-size:2.15rem; font-weight:700; letter-spacing:-.02em; line-height:1.15; margin:0 0 .35rem 0;}
.hero-meta{color:var(--suave); font-size:.92rem;}
.chip{display:inline-flex; align-items:center; gap:.4rem; padding:.28rem .7rem; border-radius:999px; font-size:.8rem;
  background:rgba(34,211,238,.08); border:1px solid rgba(34,211,238,.28); color:#bdeefa; margin:0 .35rem .35rem 0;}
.chip.neutro{background:var(--painel2); border-color:var(--borda2); color:var(--suave);}
.cit{display:inline-flex; align-items:center; gap:.35rem; font-size:.78rem; color:var(--suave);
  background:var(--painel2); border:1px solid var(--borda); border-radius:8px; padding:.12rem .5rem; margin:.15rem .3rem 0 0;}
.cit b{color:var(--ciano); font-weight:600;}
.stat{background:var(--painel); border:1px solid var(--borda); border-radius:18px; padding:1rem 1.2rem;}
.stat .n{font-size:1.9rem; font-weight:700; letter-spacing:-.02em;}
.stat .l{color:var(--suave); font-size:.82rem; margin-top:.1rem;}
.fonte{display:flex; align-items:center; gap:.65rem; padding:.55rem .65rem; border-radius:12px;
  border:1px solid var(--borda); background:var(--painel2); margin-bottom:.45rem;}
.fonte .tipo{font-size:.62rem; font-weight:700; padding:.18rem .38rem; border-radius:6px; letter-spacing:.04em;}
.fonte .tipo.pdf{background:rgba(248,113,113,.15); color:#fca5a5;}
.fonte .tipo.pptx{background:rgba(251,146,60,.15); color:#fdba74;}
.fonte .nome{font-size:.86rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1;}
.fonte .pg{font-size:.74rem; color:var(--suave);}
.usuario{display:flex; align-items:center; gap:.7rem; padding:.7rem; border-radius:16px; background:var(--painel2);
  border:1px solid var(--borda); margin-top:.4rem;}
.avatar{width:38px;height:38px;border-radius:50%;background:var(--grad);display:flex;align-items:center;
  justify-content:center;font-weight:700;color:#04111a;font-size:.9rem;flex:none;}
.usuario .nome{font-weight:600; font-size:.9rem; line-height:1.2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.usuario .email{font-size:.74rem; color:var(--suave); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.usuario > div:last-child{min-width:0;}
.guia{background:linear-gradient(135deg,rgba(34,211,238,.07),rgba(99,102,241,.09)); border:1px solid rgba(99,102,241,.28);
  border-radius:20px; padding:1.1rem 1.3rem; line-height:1.55;}
.topico{background:var(--painel2); border:1px solid var(--borda); border-radius:16px; padding:1rem 1.2rem; margin-bottom:.75rem;}
.topico .t{font-weight:600; margin-bottom:.35rem;}
.termo{display:flex; gap:.7rem; padding:.55rem 0; border-bottom:1px solid var(--borda); line-height:1.5;}
.termo:last-child{border-bottom:0}
.termo b{color:var(--ciano); min-width:9rem; max-width:9rem; flex:none;}
.nivel{font-size:.72rem; color:var(--violeta); border:1px solid rgba(167,139,250,.35); border-radius:6px; padding:.08rem .4rem;}
.aviso{color:var(--suave); font-size:.78rem; text-align:center; margin-top:.9rem;}
.vazio{color:var(--suave); text-align:center; padding:2.2rem 1rem; border:1.5px dashed var(--borda2); border-radius:18px;}

/* ---------- chat ---------- */
[data-testid="stChatMessage"]{background:transparent; padding:.45rem 0; gap:.8rem;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  background:var(--painel2); border:1px solid var(--borda); border-radius:20px; padding:.8rem 1.1rem; margin-left:12%;
}
[data-testid="stChatInput"]{background:var(--painel2); border:1px solid var(--borda2); border-radius:999px;}
[data-testid="stChatInput"]:focus-within{border-color:var(--ciano); box-shadow:0 0 0 3px rgba(34,211,238,.12);}
[data-testid="stChatInput"] textarea{background:transparent !important;}

/* ---------- inputs ---------- */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div{
  background:#0e121a !important; border-radius:12px !important; border-color:var(--borda) !important;
}
div[data-baseweb="input"]:focus-within{border-color:var(--ciano) !important; box-shadow:0 0 0 3px rgba(34,211,238,.12);}
[data-testid="stTextInput"] label p, [data-testid="stSelectbox"] label p{color:var(--suave); font-size:.82rem;}
[data-testid="stFileUploaderDropzone"]{background:var(--painel2); border:1.5px dashed #2b3750; border-radius:20px; padding:1.6rem;}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--ciano); background:#1a2234;}
button[data-baseweb="tab"]{color:var(--suave); font-weight:500;}
button[data-baseweb="tab"][aria-selected="true"]{color:#fff;}
[data-testid="stAlert"]{border-radius:14px; border:1px solid var(--borda);}
[data-testid="stMetric"]{background:var(--painel2); border:1px solid var(--borda); border-radius:16px; padding:.8rem 1rem;}
[data-testid="stProgress"] > div > div{background:var(--painel2);}
[data-testid="stRadio"] label{border-radius:10px;}
[data-testid="stTable"] table{background:var(--painel2);}
"""

CSS_LOGIN = """
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"]{display:none !important;}
.block-container{padding-top:4vh;}
"""


def aplicar(login: bool = False) -> None:
    st.markdown(f"<style>{CSS}{CSS_LOGIN if login else ''}</style>", unsafe_allow_html=True)


@lru_cache(maxsize=4)
def _b64(caminho: Path) -> str:
    return base64.b64encode(caminho.read_bytes()).decode()


def logo_html(altura: int = 44, centralizada: bool = False) -> str:
    alinhar = "text-align:center;" if centralizada else ""
    img = f'<img src="data:image/png;base64,{_b64(LOGO)}" alt="Universidade Atitus" style="height:{altura}px;{"margin:0 auto;" if centralizada else ""}">'
    return f'<div class="logo-wrap" style="{alinhar}">{img}</div>'


def icone_b64() -> str:
    return _b64(ICONE)


def e(texto: object) -> str:
    return escape(str(texto), quote=True)


def negrito_html(texto_markdown: str) -> str:
    """Escapa o texto e converte apenas **negrito** em <b>, sem abrir brecha para HTML arbitrário."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e(texto_markdown))


def iniciais(nome: str) -> str:
    partes = nome.split()
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()


def primeiro_nome(nome: str) -> str:
    return nome.split()[0] if nome.split() else nome


def saudacao_do_dia(agora: datetime | None = None) -> str:
    h = (agora or datetime.now()).hour
    return "Bom dia" if 5 <= h < 12 else "Boa tarde" if 12 <= h < 18 else "Boa noite"


def avatar_html(nome: str) -> str:
    return f'<div class="avatar">{e(iniciais(nome))}</div>'


def cartao_usuario(u: dict) -> str:
    return (f'<div class="usuario">{avatar_html(u["nome"])}<div><div class="nome">{e(u["nome"])}</div>'
            f'<div class="email">{e(u["email"])}</div></div></div>')


def chip(texto: str, neutro: bool = False) -> str:
    return f'<span class="chip{" neutro" if neutro else ""}">{e(texto)}</span>'


def citacao_html(fonte: dict) -> str:
    return f'<span class="cit">📄 {e(fonte["arquivo"])} · <b>p. {e(fonte["pagina"])}</b></span>'


def rotulo_secao(texto: str) -> str:
    return f'<div class="rotulo-secao">{e(texto)}</div>'


def painel_titulo(texto: str) -> str:
    return f'<div class="painel-titulo"><span class="ponto"></span>{e(texto)}</div>'


def data_curta(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
