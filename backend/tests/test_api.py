"""Testes dos endpoints FastAPI (auth + listagem)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from estudo_guiado.banco import Banco
from estudo_guiado.config import carregar_config
from estudo_guiado.jornada import Servico
from api.deps import get_banco, get_cfg, get_svc
from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    cfg = carregar_config()
    cfg = {**cfg, "banco": {**cfg["banco"], "caminho": str(tmp_path / "app.sqlite")},
           "cache": {**cfg["cache"], "caminho": str(tmp_path / "cache.sqlite")}}
    banco = Banco(cfg["banco"]["caminho"])
    svc = Servico(cfg)

    def _cfg():
        return cfg

    app.dependency_overrides[get_cfg] = _cfg
    app.dependency_overrides[get_banco] = lambda: banco
    # Servico usa lru_cache — sobrescreve get_svc
    app.dependency_overrides[get_svc] = lambda: svc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_criar_conta_e_login(client):
    r = client.post("/v1/usuarios", json={"nome": "Ana Souza", "email": "ana@teste.com", "senha": "senha1234"})
    assert r.status_code == 201
    assert r.json()["data"]["email"] == "ana@teste.com"

    r = client.post("/v1/sessoes", json={"email": "ana@teste.com", "senha": "senha1234"})
    assert r.status_code == 200
    token = r.json()["data"]["token"]
    me = client.get("/v1/sessoes/atual", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["nome"] == "Ana Souza"


def test_cadernos_exige_auth(client):
    assert client.get("/v1/cadernos").status_code == 401


def test_criar_caderno_e_resumo(client):
    client.post("/v1/usuarios", json={"nome": "Ana", "email": "a@b.com", "senha": "senha1234"})
    token = client.post("/v1/sessoes", json={"email": "a@b.com", "senha": "senha1234"}).json()["data"]["token"]
    h = {"Authorization": f"Bearer {token}"}
    pdf = Path(__file__).resolve().parent.parent / "uploads" / "specs__2__9220.pdf"
    if not pdf.is_file():
        pdf = Path(__file__).resolve().parents[2] / "uploads" / "specs__2__9220.pdf"
    with open(pdf, "rb") as f:
        r = client.post(
            "/v1/cadernos",
            headers=h,
            data={"titulo": "Aula teste"},
            files=[("arquivos", ("aula.pdf", f, "application/pdf"))],
        )
    assert r.status_code == 201, r.text
    cid = r.json()["data"]["id"]
    resumo = client.get(f"/v1/cadernos/{cid}/resumo", headers=h)
    assert resumo.status_code == 200
    assert "topicos" in resumo.json()["data"]
    mapa = client.get(f"/v1/cadernos/{cid}/mapa", headers=h)
    assert "dot" in mapa.json()["data"]
    cfg = client.get("/v1/configuracao").json()["data"]
    assert "limites" in cfg
