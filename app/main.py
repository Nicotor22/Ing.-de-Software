from fastapi import FastAPI
from . import models  # noqa: hace que Base "conozca" las tablas
from .database import Base, engine
from .seed import precargar_tipos_documento
from .routers import autores, ubicaciones, obras, movimientos, colecciones, documentos, prestamos, exposiciones

app = FastAPI(title="API del museo")
Base.metadata.create_all(engine)
precargar_tipos_documento()
app.include_router(autores.router)
app.include_router(ubicaciones.router)
app.include_router(obras.router)
app.include_router(movimientos.router)
app.include_router(colecciones.router)
app.include_router(documentos.router)
app.include_router(prestamos.router)
app.include_router(exposiciones.router)




@app.get("/")
def raiz():
    return {"mensaje": "Hola, museo"}