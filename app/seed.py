from sqlalchemy import select

from .database import SessionLocal
from .models import TipoDocumento, Rol
from.roles import ROLES_SISTEMA

TIPOS_DOCUMENTO = [
    "Foto",
    "Informe de Restauración",
    "Certificado de Autenticidad",
    "Catálogo Digital",
    "Documentación de Préstamo",
    "Acta de Donación",
    "Otro",
]


def precargar_tipos_documento() -> None:
    """SOLO DESARROLLO (SQLite). En la base real los precarga el script de tu equipo."""
    with SessionLocal() as db:
        existentes = set(db.scalars(select(TipoDocumento.nombre)))
        for nombre in TIPOS_DOCUMENTO:
            if nombre not in existentes:
                db.add(TipoDocumento(nombre=nombre))
        db.commit()

def precargar_roles() -> None:
    """SOLO DESARROLLO. En la base real los precarga el script de tu grupo."""
    with SessionLocal() as db:
        existentes = set(db.scalars(select(Rol.nombre)))
        for nombre in ROLES_SISTEMA:
            if nombre not in existentes:
                db.add(Rol(nombre=nombre, vigente=True))
        db.commit()