from fastapi import APIRouter, Depends

from estudo_guiado.banco import Banco

from ..deps import get_banco
from ..schemas import CriarUsuarioIn, ok

router = APIRouter(prefix="/v1/usuarios", tags=["usuarios"])


@router.post("", status_code=201)
def criar_usuario(body: CriarUsuarioIn, banco: Banco = Depends(get_banco)):
    usuario = banco.criar_usuario(body.nome, body.email, body.senha)
    return ok(usuario)
