from pydantic import BaseModel, Field

from app.schemas.paciente import PacienteRead


class BusquedaParams(BaseModel):
    cedula: str | None = Field(None, description="Cédula exacta (solo dígitos)")
    nombre: str | None = Field(None, description="Nombre o fragmento")
    q: str | None = Field(None, description="Búsqueda global (cédula o nombre)")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class BusquedaResult(BaseModel):
    encontrado: bool
    resultados: list[PacienteRead] = []
    total: int = 0
    mensaje: str | None = None


class BusquedaError(BaseModel):
    detail: str
    error_code: str = "INVALID_SEARCH"
