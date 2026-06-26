import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PacienteCreate(BaseModel):
    nombre: str = Field(..., max_length=300)
    cedula: str | None = Field(None, max_length=10, pattern=r"^\d+$")
    hospital: str | None = Field(None, max_length=300)
    piso: str | None = Field(None, max_length=20)
    habitacion: str | None = Field(None, max_length=20)
    edad: int | None = Field(None, ge=0, le=150)
    estado_salud: str | None = None
    contacto: str | None = Field(None, max_length=20)
    confianza_global: float | None = Field(None, ge=0.0, le=1.0)


class PacienteRead(BaseModel):
    id: uuid.UUID
    nombre: str
    cedula: str | None
    hospital: str | None
    piso: str | None
    habitacion: str | None
    edad: int | None
    estado_salud: str | None
    contacto: str | None
    foto_url: str | None
    status_verificacion: str
    confianza_global: float | None
    ultima_extraccion_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PacienteList(BaseModel):
    items: list[PacienteRead]
    total: int
    limit: int
    offset: int


class PacienteDetail(PacienteRead):
    total_confirmaciones: int = 0
    total_reportes: int = 0
