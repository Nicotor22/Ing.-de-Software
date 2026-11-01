from fastapi import APIRouter, Depends

from ..auth import usuario_actual
from ..models import Usuario
from ..schemas import UsuarioOut
from ..services import usuarios as servicio

router = APIRouter(tags=["CU-15 - Usuarios y roles"])


@router.get("/yo", response_model=UsuarioOut)
def mis_datos(usuario: Usuario = Depends(usuario_actual)):
    """Cualquier usuario autenticado: devuelve quién es y qué rol tiene."""
    return servicio.a_dto(usuario)