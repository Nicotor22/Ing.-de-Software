from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .models import EstadoPrestamo, TipoPrestamo

FORMATOS_DOCUMENTO = {"JPG", "PNG", "PDF"}


class AutorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    nacionalidad: str | None = None
    periodo: str | None = None
    tecnica_habitual: str | None=None
    biografia: str | None=None

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre es obligatorio")
        return valor


class AutorOut(AutorIn):
    model_config = ConfigDict(from_attributes=True)
    id: int

class UbicacionIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)

class UbicacionOut(UbicacionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int

class AutorObraIn(BaseModel):
    """Un autor dentro de una obra. Las fechas son de la relación (modelo de tu equipo)."""
    id_autor: int
    fecha_creacion: date | None = None
    fecha_finalizacion: date | None = None

    @model_validator(mode="after")
    def fechas_coherentes(self):
        if (self.fecha_creacion and self.fecha_finalizacion
                and self.fecha_finalizacion < self.fecha_creacion):
            raise ValueError("La fecha de finalización no puede ser anterior a la de creación")
        return self


class ObraIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    titulo: str = Field(min_length=1, max_length=255)
    tecnica: str | None = Field(default=None, max_length=100)
    alto: float | None = Field(default=None, gt=0)
    ancho: float | None = Field(default=None, gt=0)
    profundidad: float | None = Field(default=None, gt=0)
    periodo: str | None = Field(default=None, max_length=100)
    estado_conservacion: str | None = Field(default=None, max_length=100)
    modo_ingreso: str | None = Field(default=None, max_length=100)
    id_ubicacion_actual: int
    autores: list[AutorObraIn] = Field(min_length=1)  # extensión: al menos un autor


class AutorEnObraOut(BaseModel):
    id_autor: int
    nombre: str
    fecha_creacion: date | None = None
    fecha_finalizacion: date | None = None


class ObraOut(BaseModel):
    id: int
    titulo: str | None = None
    tecnica: str | None = None
    alto: float | None = None
    ancho: float | None = None
    profundidad: float | None = None
    periodo: str | None = None
    estado_conservacion: str | None = None
    modo_ingreso: str | None = None
    digitalizada: bool
    id_coleccion: int | None = None
    id_ubicacion_actual: int
    autores: list[AutorEnObraOut]

class MovimientoIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id_obra: int
    id_ubicacion_destino: int
    motivo: str = Field(min_length=1, max_length=300)
    responsable: str = Field(min_length=1, max_length=150)


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_obra: int
    id_ubicacion_origen: int
    id_ubicacion_destino: int
    fecha: date
    motivo: str
    responsable: str

class ColeccionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    obra_ids: list[int] = Field(min_length=1)  # extensión: al menos una obra


class ObraEnColeccionOut(BaseModel):
    id_obra: int
    titulo: str | None = None


class ColeccionOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    obras: list[ObraEnColeccionOut]

class ArchivoIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str = Field(pattern=r"^https?://", max_length=500)
    formato: str

    @field_validator("formato")
    @classmethod
    def validar_formato(cls, valor: str) -> str:
        normalizado = valor.upper().lstrip(".")
        if normalizado == "JPEG":
            normalizado = "JPG"
        if normalizado not in FORMATOS_DOCUMENTO:
            raise ValueError("Formato no soportado. Formatos válidos: JPG, PNG y PDF")
        return normalizado


class DocumentoIn(ArchivoIn):
    id_obra: int
    id_tipo_documento: int  # obligatorio: si no encaja en ninguno, se usa "Otro"


class DocumentoOut(BaseModel):
    id: int
    id_obra: int
    id_tipo_documento: int
    tipo: str
    url: str
    formato: str


class TipoDocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str

class ObraCreateIn(ObraIn):
    acta_donacion: ArchivoIn | None = None  # opcional: no toda obra es una donación

class PrestamoIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tipo: TipoPrestamo
    nombre_prestatario: str = Field(min_length=1, max_length=200)
    contacto_prestatario: str | None = Field(default=None, max_length=200)
    fecha_inicio: date
    fecha_devolucion_prevista: date
    condiciones: str = Field(min_length=1)
    id_ubicacion_destino: int
    responsable: str = Field(min_length=1, max_length=150)  # provisorio hasta CU-14
    obra_ids: list[int] = Field(default_factory=list)
    coleccion_ids: list[int] = Field(default_factory=list)
    documentacion: ArchivoIn | None = None

    @model_validator(mode="after")
    def validar_prestamo(self):
        if self.fecha_devolucion_prevista < self.fecha_inicio:
            raise ValueError("La fecha de devolución prevista no puede ser anterior a la de inicio")
        if not self.obra_ids and not self.coleccion_ids:
            raise ValueError("Hay que seleccionar al menos una obra o una colección")
        if self.tipo == TipoPrestamo.INTERINSTITUCIONAL and self.documentacion is None:
            raise ValueError("El préstamo interinstitucional requiere adjuntar documentación")
        return self


class ObraEnPrestamoOut(BaseModel):
    id_obra: int
    titulo: str | None = None


class PrestamoOut(BaseModel):
    id: int
    tipo: TipoPrestamo
    nombre_prestatario: str | None = None
    contacto_prestatario: str | None = None
    fecha_inicio: date
    fecha_devolucion_prevista: date
    fecha_devolucion_real: date | None = None
    condiciones: str
    estado: EstadoPrestamo
    obras: list[ObraEnPrestamoOut]

class DevolucionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    fecha_devolucion_real: date
    responsable: str = Field(min_length=1, max_length=150)  # provisorio hasta CU-15

class ExposicionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=1, max_length=200)
    fecha_inicio: date
    fecha_fin: date
    id_ubicacion: int
    obra_ids: list[int] = Field(default_factory=list)
    coleccion_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_exposicion(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio")
        if not self.obra_ids and not self.coleccion_ids:
            raise ValueError("Hay que seleccionar al menos una obra o una colección")
        return self


class ObraEnExposicionOut(BaseModel):
    id_obra: int
    titulo: str | None = None


class ObraExcluidaOut(BaseModel):
    id_obra: int
    titulo: str | None = None
    motivo: str


class ExposicionOut(BaseModel):
    id: int
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    id_ubicacion: int
    publicada_virtual: bool
    obras: list[ObraEnExposicionOut]


class ValidacionExposicionOut(BaseModel):
    incluidas: list[ObraEnExposicionOut]
    excluidas: list[ObraExcluidaOut]
    advertencias: list[str]


class ExposicionCreadaOut(BaseModel):
    exposicion: ExposicionOut
    excluidas: list[ObraExcluidaOut]
    advertencias: list[str]