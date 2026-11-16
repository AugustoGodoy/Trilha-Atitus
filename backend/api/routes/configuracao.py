from fastapi import APIRouter, Depends

from estudo_guiado.jornada import Servico

from ..deps import get_svc
from ..schemas import ok

router = APIRouter(prefix="/v1/configuracao", tags=["configuracao"])


@router.get("")
def configuracao(svc: Servico = Depends(get_svc)):
    lim = svc.cfg["limites"]
    return ok({
        "modo": svc.modo,
        "usar_api": svc.usar_api,
        "limites": {
            "max_paginas_por_jornada": lim["max_paginas_por_jornada"],
            "max_tamanho_arquivo_mb": lim["max_tamanho_arquivo_mb"],
            "perguntas_chat": lim["perguntas_chat"],
            "perguntas_quiz": lim["perguntas_quiz"],
            "jornadas_por_dia": lim["jornadas_por_dia"],
        },
    })
