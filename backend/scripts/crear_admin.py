"""
Crea (o promueve) un Administrador a partir del `sub` de Authly.

    python -m scripts.crear_admin <sub-uuid> ["Nombre Apellido"]

Antes levantá la API al menos una vez (crea las tablas y precarga los roles).
Si el usuario ya existe (porque entró una vez), solo se le cambia el rol.
"""
import sys
from uuid import UUID

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Rol, Usuario
from app.roles import ROL_ADMIN


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python -m scripts.crear_admin <sub-uuid> ["Nombre"]')
        sys.exit(1)
    sub = str(UUID(sys.argv[1]))  # normaliza y valida el formato
    nombre = sys.argv[2] if len(sys.argv) > 2 else None

    with SessionLocal() as db:
        rol = db.scalars(select(Rol).where(Rol.nombre == ROL_ADMIN)).first()
        if rol is None:
            print("Falta el rol Administrador: levantá la API una vez para que se precarguen los roles.")
            sys.exit(1)
        usuario = db.scalars(select(Usuario).where(Usuario.id_externo == sub)).first()
        if usuario is None:
            usuario = Usuario(id_externo=sub, nombre=nombre, id_rol=rol.id)
            db.add(usuario)
            accion = "creado como Administrador"
        else:
            usuario.id_rol = rol.id
            if nombre:
                usuario.nombre = nombre
            accion = "promovido a Administrador"
        db.commit()
        print(f"Usuario {sub} {accion}.")


if __name__ == "__main__":
    main()