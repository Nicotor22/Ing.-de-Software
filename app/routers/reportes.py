from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ReporteOut
from ..services import reportes as servicio

router = APIRouter(prefix="/reportes", tags=["CU-11 - Reporte patrimonial"])


def _filtros(
    autor_id: int | None = Query(None, description="Filtrar por autor"),
    periodo: str | None = Query(None, description="Filtrar por período de la obra"),
    tecnica: str | None = Query(None, description="Filtrar por técnica (texto parcial)"),
    exposicion_id: int | None = Query(None, description="Filtrar por exposición"),
) -> dict:
    return {
        "autor_id": autor_id,
        "periodo": periodo,
        "tecnica": tecnica,
        "exposicion_id": exposicion_id,
    }


@router.get("", response_model=ReporteOut)
def generar_reporte(filtros: dict = Depends(_filtros), db: Session = Depends(get_db)):
    """Pasos 1 a 3: el reporte en pantalla."""
    return servicio.generar_reporte(db, **filtros)


@router.get("/exportar")
def exportar_reporte(
    formato: str = Query(..., description="pdf o excel"),
    filtros: dict = Depends(_filtros),
    db: Session = Depends(get_db),
):
    """Pasos 4 y 5: descarga del archivo con los mismos filtros."""
    formato = servicio.validar_formato(formato)  # falla rápido, antes de consultar la base
    reporte = servicio.generar_reporte(db, **filtros)
    contenido, media_type, nombre = servicio.exportar_reporte(reporte, formato)
    return Response(
        content=contenido,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )