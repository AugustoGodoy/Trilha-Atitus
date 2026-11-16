"""Gera DOT Graphviz a partir do JSON do mapa mental (mesmo visual do Streamlit)."""


def mapa_para_dot(mapa: dict) -> str:
    def esc(s: str) -> str:
        return str(s).replace("\\", "").replace('"', "'")

    linhas = [
        'digraph G { bgcolor="transparent"; rankdir=LR; pad=0.2; nodesep=0.2; ranksep=0.9;',
        'node [shape=box, style="rounded,filled", fillcolor="#172033", color="#22d3ee", fontcolor="#e6e9ef", '
        'fontname="Helvetica", penwidth=1.3, margin="0.18,0.1"];',
        'edge [color="#4b5873", fontcolor="#8b93a7", fontname="Helvetica", fontsize=9, arrowsize=0.7];',
    ]
    linhas += [f'"{esc(n["id"])}" [label="{esc(n["rotulo"])}\\n(p. {n["fonte"]["pagina"]})"];' for n in mapa["nos"]]
    linhas += [f'"{esc(r["de"])}" -> "{esc(r["para"])}" [{_atributos_aresta(r["tipo"], esc)}];' for r in mapa["relacoes"]]
    return "\n".join(linhas) + "}"


def _atributos_aresta(tipo: str, esc) -> str:
    if str(tipo).lower().startswith("relaciona"):
        return "style=dashed, constraint=false, arrowhead=none"
    return f'label="{esc(tipo)}"'
