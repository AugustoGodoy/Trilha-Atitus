"""Orquestra a jornada: validação de limites, cache por hash, indexação e geração única.

Resumo, mapa e quiz são SEMPRE gerados offline (sem LLM).
O Gemini/LLM só entra em `perguntar` (etapa Dúvidas).
"""
from dataclasses import dataclass

from . import extracao, geracao
from .cache import Cache, hash_arquivos
from .chunking import Trecho, dividir
from .config import carregar_config
from .llm import ClienteLLM
from .retrieval import IndiceBM25


class LimiteExcedido(Exception):
    pass


@dataclass
class Jornada:
    hash: str
    conteudo: dict
    trechos: list[Trecho]
    indice: IndiceBM25
    do_cache: bool
    modo: str


class Servico:
    def __init__(self, cfg: dict | None = None, cache: Cache | None = None):
        self.cfg = cfg or carregar_config()
        self.cache = cache or Cache(self.cfg["cache"]["caminho"])
        self.usar_api = ClienteLLM.disponivel(self.cfg["llm"])
        self.llm = ClienteLLM(self.cfg["llm"]) if self.usar_api else None

    @property
    def modo(self) -> str:
        """Modo do chat (dúvidas). A trilha em si é sempre offline."""
        return f"chat:{self.cfg['llm']['modelo']}" if self.usar_api else "offline"

    def validar(self, arquivos: list[tuple[str, bytes]], jornadas_hoje: int | None = None) -> int:
        """Valida limites ANTES de qualquer processamento. Retorna total de páginas.

        `jornadas_hoje` é a contagem do usuário logado; sem ela, usa o contador global do cache.
        """
        lim = self.cfg["limites"]
        if not arquivos:
            raise LimiteExcedido("Envie ao menos um arquivo PDF ou PPTX.")
        hoje = self.cache.jornadas_hoje() if jornadas_hoje is None else jornadas_hoje
        if hoje >= lim["jornadas_por_dia"]:
            raise LimiteExcedido(f"Limite de {lim['jornadas_por_dia']} jornadas por dia atingido. Volte amanhã.")
        total = 0
        for nome, dados in arquivos:
            mb = len(dados) / 1_048_576
            if mb > lim["max_tamanho_arquivo_mb"]:
                raise LimiteExcedido(f"'{nome}' tem {mb:.1f} MB; o máximo é {lim['max_tamanho_arquivo_mb']} MB.")
            try:
                total += extracao.contar_paginas(nome, dados)
            except extracao.ArquivoInvalido as e:
                raise LimiteExcedido(str(e)) from e
        if total > lim["max_paginas_por_jornada"]:
            raise LimiteExcedido(
                f"O material tem {total} páginas/slides; o máximo é {lim['max_paginas_por_jornada']}. "
                "Selecione o trecho da aula que quer estudar e envie novamente.")
        return total

    def _assinatura(self) -> str:
        # Trilha sempre offline — assinatura estável (não muda com a chave Gemini)
        c, lim = self.cfg["chunking"], self.cfg["limites"]
        return f"v2|trilha-offline|{lim['perguntas_quiz']}|{c['tamanho_alvo_palavras']}|{c['sobreposicao_palavras']}"

    def preparar(self, arquivos: list[tuple[str, bytes]], jornadas_hoje: int | None = None) -> Jornada:
        self.validar(arquivos, jornadas_hoje)
        h = hash_arquivos(arquivos, self._assinatura())
        self.cache.registrar_jornada(h)
        if self.cfg["cache"]["compartilhado"] and (j := self.abrir(h)):
            return j
        return self._processar(h, arquivos)

    def abrir(self, h: str) -> Jornada | None:
        """Reabre uma jornada já processada a partir do cache, sem chamar o LLM."""
        cache = self.cache.obter(h)
        if not cache:
            return None
        trechos = [Trecho(**t) for t in cache["trechos"]]
        return Jornada(h, cache["conteudo"], trechos, IndiceBM25(trechos), True, "offline")

    def _processar(self, h: str, arquivos: list[tuple[str, bytes]]) -> Jornada:
        ch = self.cfg["chunking"]
        # Sem extrair imagens no upload: acelera muito o POST /cadernos
        paginas = [p for nome, dados in arquivos for p in extracao.extrair(nome, dados, max_imagens_por_pagina=0)]
        trechos = dividir(paginas, ch["tamanho_alvo_palavras"], ch["sobreposicao_palavras"])
        if sum(len(t.texto.split()) for t in trechos) < 30:
            raise LimiteExcedido("Quase não há texto selecionável no material (PDF escaneado?). Esta versão não suporta esse caso.")
        indice = IndiceBM25(trechos)

        # Trilha 100% offline — Gemini só no chat (perguntar)
        resumo, tin, tout = geracao.gerar_resumo(trechos, indice, None)
        self._uso(h, "resumo", tin, tout)
        mapa, tin, tout = geracao.gerar_mapa(trechos, resumo, indice, None)
        self._uso(h, "mapa", tin, tout)
        quiz, tin, tout = geracao.gerar_quiz(
            trechos, resumo, indice, None, self.cfg["limites"]["perguntas_quiz"]
        )
        self._uso(h, "quiz", tin, tout)

        conteudo = {"resumo": resumo, "mapa": mapa, "quiz": quiz, "imagens": {}}
        self.cache.salvar(h, {"conteudo": conteudo, "trechos": [t.__dict__ for t in trechos]})
        return Jornada(h, conteudo, trechos, indice, False, "offline")

    def perguntar(self, j: Jornada, pergunta: str, *, usar_gemini: bool = True) -> dict:
        """Único ponto que pode chamar o Gemini (se usar_gemini e houver chave)."""
        c = self.cfg["chunking"]
        llm = self.llm if usar_gemini else None
        r = geracao.responder(
            pergunta,
            j.indice,
            llm,
            c["trechos_recuperados"],
            c["score_minimo"],
            forcar_contexto=bool(usar_gemini and self.llm),
        )
        self._uso(j.hash, "chat", r["tokens_in"], r["tokens_out"])
        return r

    def _uso(self, h: str, etapa: str, tin: int, tout: int) -> None:
        custo = self.llm.custo_brl(tin, tout) if self.llm else 0.0
        self.cache.registrar_uso(h, etapa, tin, tout, custo)

    def custos(self, h: str) -> list[dict]:
        return self.cache.uso_por_etapa(h)
