from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import rol_actual
from ..database import get_db
from ..services import catalogo as servicio

router = APIRouter(prefix="/catalogo", tags=["CU-13 - Catálogo patrimonial"])


@router.get("")
def buscar_obras(
    autor_id: int | None = Query(None, description="Filtrar por autor"),
    tecnica: str | None = Query(None, description="Filtrar por técnica (texto parcial)"),
    periodo: str | None = Query(None, description="Filtrar por período de la obra"),
    coleccion_id: int | None = Query(None, description="Filtrar por colección"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    rol: str = Depends(rol_actual),
    db: Session = Depends(get_db),
):
    return servicio.buscar_obras(
        db, rol, autor_id=autor_id, tecnica=tecnica, periodo=periodo,
        coleccion_id=coleccion_id, limit=limit, offset=offset,
    )

@router.get("/exposiciones-virtuales")
def listar_exposiciones_virtuales(
    rol: str = Depends(rol_actual), db: Session = Depends(get_db)
):
    return servicio.listar_exposiciones_virtuales(db)


@router.get("/exposiciones-virtuales/{exposicion_id}")
def detalle_exposicion_virtual(
    exposicion_id: int, rol: str = Depends(rol_actual), db: Session = Depends(get_db)
):
    return servicio.detalle_exposicion_virtual(db, rol, exposicion_id)

@router.get("/{obra_id}")
def detalle_obra(obra_id: int, rol: str = Depends(rol_actual), db: Session = Depends(get_db)):
    return servicio.detalle_obra(db, rol, obra_id)