"""CRUD de cadernos e endpoints do Estúdio (resumo, mapa, quiz, chat)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from estudo_guiado import geracao
from estudo_guiado.banco import Banco
from estudo_guiado.jornada import Servico

from ..deps import get_banco, get_svc, jornada_do_caderno, resumo_das_fontes, usuario_atual
from ..errors import ApiError
from ..graphviz_dot import mapa_para_dot
from ..schemas import CorrecaoQuizIn, PerguntaIn, RenomearCadernoIn, ok

router = APIRouter(prefix="/v1/cadernos", tags=["cadernos"])


def _serial_caderno(caderno: dict, jornada=None, restantes: int | None = None, do_cache: bool | None = None) -> dict:
    out = dict(caderno)
    if jornada is not None:
        fontes = resumo_das_fontes(jornada)
        out["fontes"] = [{"arquivo": a, "paginas": p} for a, p in fontes.items()]
        out["total_paginas"] = sum(fontes.values())
    if restantes is not None:
        out["restantes"] = restantes
    if do_cache is not None:
        out["do_cache"] = do_cache
    return out


@router.get("")
def listar(
    limit: int = 20,
    offset: int = 0,
    usuario: dict = Depends(usuario_atual),
    banco: Banco = Depends(get_banco),
):
    todos = banco.listar_cadernos(usuario["id"])
    fatia = todos[offset : offset + limit]
    return ok(
        fatia,
        meta={"total": len(todos), "limit": limit, "offset": offset},
        links={"self": f"/v1/cadernos?limit={limit}&offset={offset}"},
    )


@router.post("", status_code=201)
async def criar(
    arquivos: list[UploadFile] = File(...),
    titulo: str = Form(""),
    usuario: dict = Depends(usuario_atual),
    banco: Banco = Depends(get_banco),
    svc: Servico = Depends(get_svc),
):
    if not arquivos:
        raise ApiError(400, "INVALID_INPUT", "Envie ao menos um arquivo PDF ou PPTX.")
    pares: list[tuple[str, bytes]] = []
    for arq in arquivos:
        dados = await arq.read()
        pares.append((arq.filename or "arquivo.pdf", dados))
    jornada = svc.preparar(pares, jornadas_hoje=banco.cadernos_criados_hoje(usuario["id"]))
    nome = " ".join(titulo.split()) or _titulo_padrao([n for n, _ in pares])
    caderno_id = banco.registrar_caderno(usuario["id"], jornada.hash, nome)
    caderno = banco.caderno(usuario["id"], caderno_id)
    total = svc.cfg["limites"]["perguntas_chat"]
    restantes = max(0, total - banco.perguntas_consumidas(caderno_id))
    body = ok(_serial_caderno(caderno, jornada, restantes, jornada.do_cache))
    return JSONResponse(status_code=201, content=body, headers={"Location": f"/v1/cadernos/{caderno_id}"})


def _titulo_padrao(nomes: list[str]) -> str:
    base = Path(nomes[0]).stem if nomes else "Caderno"
    return base[:80]


@router.get("/{caderno_id}")
def obter(caderno_id: int, usuario: dict = Depends(usuario_atual),
          banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    caderno, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    total = svc.cfg["limites"]["perguntas_chat"]
    restantes = max(0, total - banco.perguntas_consumidas(caderno_id))
    return ok(_serial_caderno(caderno, jornada, restantes, jornada.do_cache))


@router.patch("/{caderno_id}")
def renomear(caderno_id: int, body: RenomearCadernoIn, usuario: dict = Depends(usuario_atual),
             banco: Banco = Depends(get_banco)):
    if not banco.caderno(usuario["id"], caderno_id):
        raise ApiError(404, "NOT_FOUND", "Caderno não encontrado.")
    banco.renomear_caderno(usuario["id"], caderno_id, body.titulo)
    return ok(banco.caderno(usuario["id"], caderno_id))


@router.delete("/{caderno_id}", status_code=204)
def excluir(caderno_id: int, usuario: dict = Depends(usuario_atual), banco: Banco = Depends(get_banco)):
    if not banco.caderno(usuario["id"], caderno_id):
        raise ApiError(404, "NOT_FOUND", "Caderno não encontrado.")
    banco.excluir_caderno(usuario["id"], caderno_id)
    return None


@router.get("/{caderno_id}/resumo")
def resumo(caderno_id: int, usuario: dict = Depends(usuario_atual),
           banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    _, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    r = jornada.conteudo["resumo"]
    termos = [t["termo"] for t in r["termos"]]
    topicos = []
    for tp in r["topicos"]:
        topicos.append({
            **tp,
            "texto_destacado": geracao.destacar_termos(tp["texto"], termos),
        })
    return ok({"topicos": topicos, "termos": r["termos"]})


@router.get("/{caderno_id}/mapa")
def mapa(caderno_id: int, usuario: dict = Depends(usuario_atual),
         banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    _, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    m = jornada.conteudo["mapa"]
    return ok({"mapa": m, "dot": mapa_para_dot(m)})


@router.get("/{caderno_id}/mapa/trecho")
def trecho_no(caderno_id: int, no_id: str, usuario: dict = Depends(usuario_atual),
              banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    _, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    por_id = {n["id"]: n for n in jornada.conteudo["mapa"]["nos"]}
    if no_id not in por_id:
        raise ApiError(404, "NOT_FOUND", "Nó não encontrado.")
    f = por_id[no_id]["fonte"]
    texto = "\n\n".join(
        t.texto for t in jornada.trechos if t.arquivo == f["arquivo"] and t.pagina == f["pagina"]
    )[:1200]
    chave = f"{f['arquivo']}|{f['pagina']}"
    imgs = jornada.conteudo.get("imagens", {}).get(chave, [])[:2]
    return ok({
        "no": por_id[no_id],
        "texto": texto,
        "imagens": [f"/v1/cadernos/{caderno_id}/imagens/{f['arquivo']}/{f['pagina']}?i={i}" for i, _ in enumerate(imgs)],
    })


@router.get("/{caderno_id}/quiz")
def quiz(caderno_id: int, usuario: dict = Depends(usuario_atual),
         banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    caderno, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    resultados = banco.resultados_quiz(caderno_id)
    return ok({
        "quiz": jornada.conteudo["quiz"],
        "resultados": resultados,
    })


@router.post("/{caderno_id}/quiz/correcoes")
def corrigir(caderno_id: int, body: CorrecaoQuizIn, usuario: dict = Depends(usuario_atual),
             banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    _, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    quiz = jornada.conteudo["quiz"]
    # JSON keys viram str; normaliza para int
    respostas = {int(k): v for k, v in body.respostas.items()}
    resultado = geracao.corrigir_quiz(quiz, respostas)
    banco.salvar_resultado_quiz(caderno_id, resultado["nota"], resultado["acertos"], resultado["total"])
    return ok(resultado)


@router.get("/{caderno_id}/mensagens")
def mensagens(caderno_id: int, usuario: dict = Depends(usuario_atual),
              banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    jornada_do_caderno(svc, banco, usuario, caderno_id)
    return ok(banco.listar_mensagens(caderno_id))


@router.post("/{caderno_id}/mensagens")
def perguntar(caderno_id: int, body: PerguntaIn, usuario: dict = Depends(usuario_atual),
              banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    caderno, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    total = svc.cfg["limites"]["perguntas_chat"]
    restantes = max(0, total - banco.perguntas_consumidas(caderno_id))
    if restantes <= 0:
        raise ApiError(429, "LIMITE_CHAT", "Você usou todas as perguntas deste caderno.")
    pergunta = body.pergunta.strip()
    if not pergunta:
        raise ApiError(400, "INVALID_INPUT", "Informe uma pergunta.")
    r = svc.perguntar(jornada, pergunta, usar_gemini=body.usar_gemini)
    consumiu = not r["sem_base"] or svc.cfg["limites"]["recusa_consome_pergunta"]
    banco.salvar_mensagem(caderno_id, pergunta, r, consumiu)
    restantes = max(0, total - banco.perguntas_consumidas(caderno_id))
    return ok({
        "pergunta": pergunta,
        "resposta": r["resposta"],
        "fontes": r["fontes"],
        "sem_base": r["sem_base"],
        "restantes": restantes,
        "provedor": r.get("provedor", "desconhecido"),
        "modelo": r.get("modelo") or None,
        "usar_gemini": body.usar_gemini,
    })


@router.get("/{caderno_id}/sugestoes")
def sugestoes(caderno_id: int, usuario: dict = Depends(usuario_atual),
              banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    _, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    minimo = svc.cfg["chunking"]["score_minimo"]
    candidatas = (f"O que é {t['termo']}?" for t in jornada.conteudo["resumo"]["termos"])
    aprovadas = [q for q in candidatas if (achados := jornada.indice.buscar(q, 1)) and achados[0][1] >= minimo]
    return ok(aprovadas[:3])


@router.get("/{caderno_id}/custos")
def custos(caderno_id: int, usuario: dict = Depends(usuario_atual),
           banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    caderno, _ = jornada_do_caderno(svc, banco, usuario, caderno_id)
    uso = svc.custos(caderno["hash"])
    return ok({"itens": uso, "total_brl": round(sum(u["custo_brl"] for u in uso), 4)})


@router.get("/{caderno_id}/imagens/{arquivo}/{pagina}")
def imagem(caderno_id: int, arquivo: str, pagina: int, i: int = 0,
           usuario: dict = Depends(usuario_atual),
           banco: Banco = Depends(get_banco), svc: Servico = Depends(get_svc)):
    _, jornada = jornada_do_caderno(svc, banco, usuario, caderno_id)
    chave = f"{arquivo}|{pagina}"
    imgs = jornada.conteudo.get("imagens", {}).get(chave, [])
    if i < 0 or i >= len(imgs):
        raise ApiError(404, "NOT_FOUND", "Imagem não encontrada.")
    path = Path(imgs[i])
    if not path.is_file():
        raise ApiError(404, "NOT_FOUND", "Arquivo de imagem ausente.")
    return FileResponse(path)
