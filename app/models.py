import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum

from .database import Base

def pk(nombre_columna: str):
    return mapped_column(nombre_columna, primary_key=True, default=uuid)


class Autor(Base):
    __tablename__ = "autor"
 
    id: Mapped[uuid.UUID] = pk("id_autor")
    nombre: Mapped[str] = mapped_column(String(200))  # sin UNIQUE (CU-02)
    nacionalidad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    periodo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tecnica_habitual: Mapped[str | None] = mapped_column(String(100), nullable=True)
    biografia: Mapped[str | None] = mapped_column(Text, nullable=True)


class Coleccion(Base):
    __tablename__ = "coleccion"
 
    id: Mapped[uuid.UUID] = pk("id_coleccion")
    nombre: Mapped[str] = mapped_column(String(150), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
 
    obras: Mapped[list["Obra"]] = relationship(back_populates="coleccion")


class Ubicacion(Base):
    __tablename__ = "ubicacion"
 
    id: Mapped[uuid.UUID] = pk("id_ubicacion")
    nombre: Mapped[str] = mapped_column(String(150))


class ObraAutor(Base):
    """Tabla intermedia con atributos propios, por eso es una clase y no un Table."""
    __tablename__ = "obra_autor"
 
    id_obra: Mapped[uuid.UUID] = mapped_column(ForeignKey("obra.id_obra"), primary_key=True)
    id_autor: Mapped[uuid.UUID] = mapped_column(ForeignKey("autor.id_autor"), primary_key=True)
    fecha_creacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_finalizacion: Mapped[date | None] = mapped_column(Date, nullable=True)
 
    autor: Mapped[Autor] = relationship()


class Obra(Base):
    __tablename__ = "obra"
 
    id: Mapped[uuid.UUID] = pk("id_obra")
    # Los campos "a confirmar" quedan opcionales hasta que el equipo decida
    titulo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tecnica: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alto: Mapped[float | None] = mapped_column(Float, nullable=True)
    ancho: Mapped[float | None] = mapped_column(Float, nullable=True)
    profundidad: Mapped[float | None] = mapped_column(Float, nullable=True)
    periodo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado_conservacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modo_ingreso: Mapped[str | None] = mapped_column(String(100), nullable=True)
    digitalizada: Mapped[bool] = mapped_column(Boolean, default=False)  # CU-12
 
    id_coleccion: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("coleccion.id_coleccion"), nullable=True
    )
    # Obligatoria: una obra no se puede crear sin ubicación (CU-04)
    id_ubicacion_actual: Mapped[uuid.UUID] = mapped_column(ForeignKey("ubicacion.id_ubicacion"))
 
    coleccion: Mapped[Coleccion | None] = relationship(back_populates="obras")
    ubicacion_actual: Mapped[Ubicacion] = relationship()
    autores: Mapped[list[ObraAutor]] = relationship(cascade="all, delete-orphan")
    documentos: Mapped[list["Documento"]] = relationship(cascade="all, delete-orphan")

class Movimiento(Base):
    __tablename__ = "movimiento"
 
    id: Mapped[uuid.UUID] = pk("id_movimiento")
    id_obra: Mapped[uuid.UUID] = mapped_column(ForeignKey("obra.id_obra"))
    id_ubicacion_origen: Mapped[uuid.UUID] = mapped_column(ForeignKey("ubicacion.id_ubicacion"))
    id_ubicacion_destino: Mapped[uuid.UUID] = mapped_column(ForeignKey("ubicacion.id_ubicacion"))
    fecha: Mapped[date] = mapped_column(Date)
    motivo: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(150))  # texto provisorio hasta CU-15

class TipoDocumento(Base):
    __tablename__ = "tipo_documento"
 
    id: Mapped[uuid.UUID] = pk("id_tipo_documento")
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class Documento(Base):
    __tablename__ = "documento"
 
    id: Mapped[uuid.UUID] = pk("id_documento")
    id_obra: Mapped[uuid.UUID] = mapped_column(ForeignKey("obra.id_obra"))
    id_tipo_documento: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tipo_documento.id_tipo_documento")
    )
    url: Mapped[str] = mapped_column(String(500))  # enlace al repositorio externo
    formato: Mapped[str] = mapped_column(String(10))  # JPG, PNG o PDF
 
    tipo: Mapped[TipoDocumento] = relationship()


class TipoPrestamo(str, enum.Enum):
    INTERNO = "INTERNO"
    INTERINSTITUCIONAL = "INTERINSTITUCIONAL"


class EstadoPrestamo(str, enum.Enum):
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"


class Prestamo(Base):
    __tablename__ = "prestamo"
 
    id: Mapped[uuid.UUID] = pk("id_prestamo")
    nombre_prestatario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contacto_prestatario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo: Mapped[TipoPrestamo] = mapped_column(SAEnum(TipoPrestamo, native_enum=False, length=20))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_devolucion_prevista: Mapped[date] = mapped_column(Date)
    fecha_devolucion_real: Mapped[date | None] = mapped_column(Date, nullable=True)  # CU-07
    condiciones: Mapped[str] = mapped_column(Text)
    estado: Mapped[EstadoPrestamo] = mapped_column(
        SAEnum(EstadoPrestamo, native_enum=False, length=20), default=EstadoPrestamo.ACTIVO
    )
 
    obras: Mapped[list["PrestamoObra"]] = relationship(cascade="all, delete-orphan")


class PrestamoObra(Base):
    __tablename__ = "prestamo_obra"
 
    id_prestamo: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prestamo.id_prestamo"), primary_key=True
    )
    id_obra: Mapped[uuid.UUID] = mapped_column(ForeignKey("obra.id_obra"), primary_key=True)
 
    obra: Mapped[Obra] = relationship()

class Exposicion(Base):
    __tablename__ = "exposicion"
 
    id: Mapped[uuid.UUID] = pk("id_exposicion")
    nombre: Mapped[str] = mapped_column(String(200))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    id_ubicacion: Mapped[uuid.UUID] = mapped_column(ForeignKey("ubicacion.id_ubicacion"))  # la sala
    publicada_virtual: Mapped[bool] = mapped_column(Boolean, default=False)  # CU-14
 
    ubicacion: Mapped[Ubicacion] = relationship()
    obras: Mapped[list["ExposicionObra"]] = relationship(cascade="all, delete-orphan")


class ExposicionObra(Base):
    __tablename__ = "exposicion_obra"
 
    id_exposicion: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exposicion.id_exposicion"), primary_key=True
    )
    id_obra: Mapped[uuid.UUID] = mapped_column(ForeignKey("obra.id_obra"), primary_key=True)
 
    obra: Mapped[Obra] = relationship()

class EstadoRestauracion(str, enum.Enum):
    ACTIVA = "ACTIVA"
    FINALIZADA = "FINALIZADA"


class Restauracion(Base):
    __tablename__ = "restauracion"
 
    id: Mapped[uuid.UUID] = pk("id_restauracion")
    id_obra: Mapped[uuid.UUID] = mapped_column(ForeignKey("obra.id_obra"))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_prevista_devolucion: Mapped[date] = mapped_column(Date)
    tecnica_aplicada: Mapped[str] = mapped_column(String(200))
    responsable: Mapped[str] = mapped_column(String(150))  # interno o restaurador externo
    # NULL = informe pendiente
    id_documento_informe: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documento.id_documento"), nullable=True
    )
    # --- Propuestas (las pide el CU-10; no están en el modelo de tu equipo todavía) ---
    estado: Mapped[EstadoRestauracion] = mapped_column(
        SAEnum(EstadoRestauracion, native_enum=False, length=20),
        default=EstadoRestauracion.ACTIVA,
    )
    fecha_regreso_real: Mapped[date | None] = mapped_column(Date, nullable=True)

class Rol(Base):
    __tablename__ = "rol"

    id: Mapped[uuid.UUID] = pk("id_rol")
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = pk("id_usuario")
    id_externo: Mapped[str] = mapped_column(String(36), unique=True)  # el "sub" de Authly
    nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    id_rol: Mapped[uuid.UUID]

    rol: Mapped[Rol] = relationship()