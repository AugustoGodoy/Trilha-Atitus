"""Cliente LLM compatível com a API OpenAI (chave só no servidor). Sem dependências extras."""
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class ErroLLM(Exception):
    pass


@dataclass
class Resposta:
    dados: dict
    tokens_in: int
    tokens_out: int


class ClienteLLM:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.chave = os.environ.get(cfg["chave_env"], "")

    @staticmethod
    def disponivel(cfg: dict) -> bool:
        if cfg["provider"] == "offline":
            return False
        return bool(os.environ.get(cfg["chave_env"]))

    def custo_brl(self, tin: int, tout: int) -> float:
        c = self.cfg
        usd = tin / 1e6 * c["preco_entrada_por_milhao"] + tout / 1e6 * c["preco_saida_por_milhao"]
        return round(usd * c["cambio_brl"], 6)

    def _modelos(self) -> list[str]:
        principal = self.cfg["modelo"]
        fallback = str(self.cfg.get("modelo_fallback") or "").strip()
        out = [principal]
        if fallback and fallback != principal:
            out.append(fallback)
        return out

    def json(self, sistema: str, usuario: str) -> Resposta:
        ultimo: ErroLLM | None = None
        for modelo in self._modelos():
            for tentativa in range(3):
                try:
                    return self._chamar(modelo, sistema, usuario)
                except ErroLLM as e:
                    ultimo = e
                    msg = str(e)
                    # Alta demanda / rate limit → espera e tenta de novo
                    if "HTTP 503" in msg or "HTTP 429" in msg or "UNAVAILABLE" in msg:
                        time.sleep(1.2 * (2 ** tentativa))
                        continue
                    break  # erro definitivo neste modelo → tenta fallback
        raise ultimo or ErroLLM("Falha ao chamar o modelo.")

    def _chamar(self, modelo: str, sistema: str, usuario: str) -> Resposta:
        corpo = {
            "model": modelo,
            "temperature": self.cfg["temperatura"],
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        }
        req = urllib.request.Request(
            self.cfg["base_url"].rstrip("/") + "/chat/completions",
            data=json.dumps(corpo).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.chave}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                dados = json.load(r)
        except urllib.error.HTTPError as e:
            corpo_erro = e.read().decode("utf-8", errors="replace")[:500]
            raise ErroLLM(f"Falha ao chamar o modelo (HTTP {e.code}): {corpo_erro}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise ErroLLM(f"Falha ao chamar o modelo: {e}") from e
        texto = dados["choices"][0]["message"]["content"]
        texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
        try:
            obj = json.loads(texto)
        except json.JSONDecodeError as e:
            raise ErroLLM("O modelo devolveu um JSON inválido.") from e
        uso = dados.get("usage", {})
        return Resposta(obj, uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0))
