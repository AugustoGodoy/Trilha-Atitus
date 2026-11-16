from fastapi import APIRouter, Depends

from estudo_guiado.banco import Banco

from ..deps import get_banco, usuario_atual
from ..schemas import ok

router = APIRouter(prefix="/v1/estatisticas", tags=["estatisticas"])


@router.get("")
def estatisticas(usuario: dict = Depends(usuario_atual), banco: Banco = Depends(get_banco)):
    dados = banco.estatisticas(usuario["id"])
    dados["cadernos_hoje"] = banco.cadernos_criados_hoje(usuario["id"])
    return ok(dados)
