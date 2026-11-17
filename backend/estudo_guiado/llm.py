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
    modelo: str = ""


# Ordem de tentativa se o principal/fallback do config falharem (IDs mudam com o tempo)
MODELOS_RESERVA = (
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)


class ClienteLLM:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.chave = os.environ.get(cfg["chave_env"], "").strip()
        self._modelos_api: list[str] | None = None

    @staticmethod
    def disponivel(cfg: dict) -> bool:
        if cfg["provider"] == "offline":
            return False
        return bool(os.environ.get(cfg["chave_env"], "").strip())

    def custo_brl(self, tin: int, tout: int) -> float:
        c = self.cfg
        usd = tin / 1e6 * c["preco_entrada_por_milhao"] + tout / 1e6 * c["preco_saida_por_milhao"]
        return round(usd * c["cambio_brl"], 6)

    def _base(self) -> str:
        return self.cfg["base_url"].rstrip("/")

    def _modelos(self) -> list[str]:
        principal = str(self.cfg.get("modelo") or "").strip()
        fallback = str(self.cfg.get("modelo_fallback") or "").strip()
        out: list[str] = []
        for m in (principal, fallback, *MODELOS_RESERVA):
            if m and m not in out:
                out.append(m)
        if self._modelos_api:
            for m in self._modelos_api:
                if m not in out and "embed" not in m.lower() and "tts" not in m.lower():
                    out.append(m)
        return out

    def listar_modelos_api(self) -> list[str]:
        req = urllib.request.Request(
            self._base() + "/models",
            headers={"Authorization": f"Bearer {self.chave}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                dados = json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return []
        ids = []
        for item in dados.get("data") or []:
            mid = str(item.get("id") or "").strip()
            if mid:
                ids.append(mid.removeprefix("models/"))
        self._modelos_api = ids
        return ids

    def json(self, sistema: str, usuario: str) -> Resposta:
        ultimo: ErroLLM | None = None
        modelos = self._modelos()
        for rodada in range(2):
            for modelo in modelos:
                for com_format in (True, False):
                    for tentativa in range(2):
                        try:
                            return self._chamar(modelo, sistema, usuario, com_json_format=com_format)
                        except ErroLLM as e:
                            ultimo = e
                            msg = str(e)
                            if "HTTP 503" in msg or "HTTP 429" in msg or "UNAVAILABLE" in msg:
                                time.sleep(0.8 * (2 ** tentativa))
                                continue
                            if "HTTP 404" in msg or "NOT_FOUND" in msg:
                                break  # próximo modelo
                            if com_format and ("HTTP 400" in msg or "response_format" in msg.lower()):
                                break  # tenta sem response_format
                            break
                    else:
                        continue
                    break
            # Se tudo deu 404, consulta a lista real de modelos e tenta de novo
            if rodada == 0 and ultimo and ("404" in str(ultimo) or "NOT_FOUND" in str(ultimo)):
                descobertos = self.listar_modelos_api()
                if descobertos:
                    modelos = [m for m in descobertos if "gemini" in m.lower() and "embed" not in m.lower()]
                    continue
            break
        raise ultimo or ErroLLM("Falha ao chamar o modelo.")

    def _chamar(self, modelo: str, sistema: str, usuario: str, *, com_json_format: bool) -> Resposta:
        corpo: dict = {
            "model": modelo,
            "temperature": self.cfg["temperatura"],
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        }
        if com_json_format:
            corpo["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            self._base() + "/chat/completions",
            data=json.dumps(corpo).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.chave}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
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
        return Resposta(obj, uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0), modelo=modelo)
