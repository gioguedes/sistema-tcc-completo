from fastapi import APIRouter, Depends
from sqlalchemy import select

from src.api.dependencias import Sessao, usuario_atual
from src.api.esquemas import EspecieSaida
from src.db.models import Especie

router = APIRouter(tags=["catalogos"], dependencies=[Depends(usuario_atual)])


@router.get("/especies", response_model=list[EspecieSaida])
def listar_especies(sessao: Sessao) -> list[Especie]:
    return list(sessao.scalars(select(Especie).order_by(Especie.nome_comum)))
