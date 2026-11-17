from sqlalchemy import select, text
from app.database import Base, SessionLocal, engine
from app.models import Rol, TipoDocumento
from app.roles import ROLES_SISTEMA
from app.services.documentos import (
    TIPO_ACTA,
    TIPO_FOTO,
    TIPO_INFORME,
    TIPO_PRESTAMO,
)


def crear_enums_y_tablas() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE estado_conservacion_t AS ENUM ('Excelente', 'Muy bueno', 'Bueno', 'Malo');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE modo_ingreso_t AS ENUM ('Donación', 'Adquisición', 'Legado');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE tipo_prestamo_t AS ENUM ('Interno', 'Interinstitucional');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
    Base.metadata.create_all(bind=engine)


def precargar_datos() -> None:
    tipos_doc_iniciales = [
        TIPO_ACTA,
        TIPO_PRESTAMO,
        TIPO_INFORME,
        TIPO_FOTO,
        "Catálogo Digital",
        "Certificado de Autenticidad",
        "Otro",
    ]

    with SessionLocal() as db:
        for nombre_rol in ROLES_SISTEMA:
            existe = db.scalars(select(Rol).where(Rol.nombre == nombre_rol)).first()
            if not existe:
                db.add(Rol(nombre=nombre_rol, vigente=True))

        for nombre_tipo in tipos_doc_iniciales:
            existe = db.scalars(
                select(TipoDocumento).where(TipoDocumento.nombre == nombre_tipo)
            ).first()
            if not existe:
                db.add(TipoDocumento(nombre=nombre_tipo))

        db.commit()


if __name__ == "__main__":
    crear_enums_y_tablas()
    precargar_datos()
    print("Tablas, ENUMs, roles y tipos de documento creados correctamente.")