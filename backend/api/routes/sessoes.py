from fastapi import APIRouter, Depends

from estudo_guiado.banco import Banco

from ..deps import get_banco, usuario_atual
from ..schemas import SessaoIn, ok

router = APIRouter(prefix="/v1/sessoes", tags=["sessoes"])


@router.post("")
def entrar(body: SessaoIn, banco: Banco = Depends(get_banco)):
    usuario = banco.autenticar(body.email, body.senha)
    token = banco.criar_sessao(usuario["id"])
    return ok({"token": token, "usuario": usuario})


@router.get("/atual")
def atual(usuario: dict = Depends(usuario_atual)):
    limpo = {k: v for k, v in usuario.items() if k != "_token"}
    return ok(limpo)


@router.delete("/atual", status_code=204)
def sair(usuario: dict = Depends(usuario_atual), banco: Banco = Depends(get_banco)):
    banco.encerrar_sessao(usuario["_token"])
    return None
