from sqlalchemy import text

from app.database import engine

with engine.connect() as conexion:
    print(conexion.execute(text("select version()")).scalar())