from fastapi import FastAPI
from . import models  # noqa: hace que Base "conozca" las tablas
from .database import Base, engine
from .seed import precargar_tipos_documento, precargar_roles
from .routers import autores, ubicaciones, obras, movimientos, colecciones, documentos, prestamos, exposiciones, restauraciones, digitalizacion, reportes, catalogo, usuarios

app = FastAPI(title="API del museo")
Base.metadata.create_all(engine)
precargar_tipos_documento()
precargar_roles()
app.include_router(autores.router)
app.include_router(ubicaciones.router)
app.include_router(obras.router)
app.include_router(movimientos.router)
app.include_router(colecciones.router)
app.include_router(documentos.router)
app.include_router(prestamos.router)
app.include_router(exposiciones.router)
app.include_router(restauraciones.router)
app.include_router(digitalizacion.router)
app.include_router(reportes.router)
app.include_router(catalogo.router)
app.include_router(usuarios.router)


@app.get("/")
def raiz():
    return {"mensaje": "Hola, museo"}