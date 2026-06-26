import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VerificacionCreate(BaseModel):
    tipo: str = Field(
        ..., pattern=r"^(confirmar|reportar_error)$",
        description="'confirmar' si los datos son correctos, 'reportar_error' si hay error",
    )
    verificador_id: str = Field(
        ..., max_length=64,
        description="Identificador del dispositivo (fingerprinting básico)",
    )
    comentario: str | None = Field(
        None, max_length=500,
        description="Obligatorio si tipo=reportar_error",
    )


class VerificacionRead(BaseModel):
    id: uuid.UUID
    paciente_id: uuid.UUID
    verificador_id: str
    tipo: str
    comentario: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VerificacionStats(BaseModel):
    paciente_id: uuid.UUID
    status_verificacion: str
    total_confirmaciones: int = 0
    total_reportes: int = 0
