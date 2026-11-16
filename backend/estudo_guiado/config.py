import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_config(caminho: Path | None = None) -> dict:
    caminho = caminho or RAIZ / "config.toml"
    with open(caminho, "rb") as f:
        cfg = tomllib.load(f)
    for secao in ("cache", "banco"):
        if secao in cfg and "caminho" in cfg[secao]:
            p = Path(cfg[secao]["caminho"])
            if not p.is_absolute():
                cfg[secao]["caminho"] = str((RAIZ / p).resolve())
    return cfg
