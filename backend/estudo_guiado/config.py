import os
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_config(caminho: Path | None = None) -> dict:
    caminho = caminho or RAIZ / "config.toml"
    with open(caminho, "rb") as f:
        cfg = tomllib.load(f)
    # Persistência no Railway: monte um Volume em /data e defina TRILHA_DATA_DIR=/data
    data_dir = os.environ.get("TRILHA_DATA_DIR", "").strip()
    base = Path(data_dir).resolve() if data_dir else None
    for secao, nome_arquivo in (("cache", "cache.sqlite"), ("banco", "app.sqlite")):
        if secao not in cfg or "caminho" not in cfg[secao]:
            continue
        if base is not None:
            cfg[secao]["caminho"] = str(base / nome_arquivo)
            continue
        p = Path(cfg[secao]["caminho"])
        if not p.is_absolute():
            cfg[secao]["caminho"] = str((RAIZ / p).resolve())
    return cfg
