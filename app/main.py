from fastapi import FastAPI
from .database import Base, engine
from .routers import autores, ubicaciones, obras, movimientos, colecciones, documentos, prestamos, exposiciones, restauraciones, digitalizacion, reportes, catalogo, usuarios
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="API del museo")


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

@app.exception_handler(StarletteHTTPException)
async def manejar_http(request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": jsonable_encoder(exc.detail)},
        headers=getattr(exc, "headers", None),
    )