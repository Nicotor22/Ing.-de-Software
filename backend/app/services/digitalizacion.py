from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Obra
from ..schemas import DigitalizacionIn
from . import documentos as docs

# PROVISORIO: el estándar de calidad no está definido (CU-12, "Requisitos Especiales")
FORMATOS_IMAGEN = {"JPG", "PNG"}
LADO_MAYOR_MINIMO_PX = 2000


def _obtener_obra(db: Session, obra_id: int, bloquear: bool = False) -> Obra:
    obra = db.get(Obra, obra_id, with_for_update=bloquear)
    if obra is None:
        raise HTTPException(status_code=404, detail="La obra no existe")
    return obra


def evaluar_calidad(datos: DigitalizacionIn) -> list[str]:
    """Paso 3: devuelve la lista de problemas (vacía si cumple el estándar)."""
    problemas = []
    if datos.formato not in FORMATOS_IMAGEN:
        problemas.append("La digitalización tiene que ser una imagen JPG o PNG")
    if max(datos.ancho_px, datos.alto_px) < LADO_MAYOR_MINIMO_PX:
        problemas.append(
            f"Resolución insuficiente: {datos.ancho_px}x{datos.alto_px}px "
            f"(el lado mayor debe ser de al menos {LADO_MAYOR_MINIMO_PX}px)"
        )
    return problemas


def validar_digitalizacion(db: Session, obra_id: int, datos: DigitalizacionIn) -> dict:
    """Pasos 1 a 3 sin guardar nada: lo que el administrador ve antes de confirmar."""
    _obtener_obra(db, obra_id)
    problemas = evaluar_calidad(datos)
    return {"cumple": not problemas, "problemas": problemas}


def digitalizar_obra(db: Session, obra_id: int, datos: DigitalizacionIn) -> Obra:
    """Paso 6: se repite la validación y se guarda TODO junto."""
    obra = _obtener_obra(db, obra_id, bloquear=True)

    problemas = evaluar_calidad(datos)
    if problemas:
        # Extensión del paso 3: se rechaza y la obra NO se marca
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": "El archivo no cumple el estándar mínimo de calidad; "
                           "la obra no fue marcada como digitalizada",
                "problemas": problemas,
            },
        )

    id_tipo_foto = docs.id_tipo_por_nombre(db, docs.TIPO_FOTO)
    try:
        # <<include>> Vincular Documentación Multimedia (sin commit propio)
        docs.agregar_documento(db, obra, id_tipo_foto, datos.url, datos.formato)
        obra.digitalizada = True
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la digitalización; la obra no fue marcada como "
                   "digitalizada. Podés reintentar",
        )
    db.refresh(obra)
    return obra