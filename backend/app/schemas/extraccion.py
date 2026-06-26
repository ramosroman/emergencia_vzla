import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CampoExtraido(BaseModel):
    """Representa un campo extraído con su valor, confianza y texto original."""
    valor: str | None = None
    confianza: float | None = Field(None, ge=0.0, le=1.0)
    raw_text: str | None = None


class PacienteExtraido(BaseModel):
    """Paciente extraído por Gemini. Todos los campos son opcionales
    porque Gemini podría no encontrar toda la información en la imagen."""
    nombre: CampoExtraido = CampoExtraido()
    cedula: CampoExtraido = CampoExtraido()
    hospital: CampoExtraido = CampoExtraido()
    piso: CampoExtraido = CampoExtraido()
    habitacion: CampoExtraido = CampoExtraido()
    edad: CampoExtraido = CampoExtraido()
    estado_salud: CampoExtraido = CampoExtraido()
    contacto: CampoExtraido = CampoExtraido()
    notas: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, values: dict) -> dict:
        """Convierte null/{} de Gemini al formato esperado por Pydantic."""
        # Campos CampoExtraido: convertir None a {} para que Pydantic use defaults
        campo_fields = {"nombre", "cedula", "hospital", "piso",
                        "habitacion", "edad", "estado_salud", "contacto"}
        for field_name in campo_fields:
            if field_name in values and values[field_name] is None:
                values[field_name] = {}
        # notas: convertir null o {} (Gemini confunde el tipo) a None
        if "notas" in values:
            if values["notas"] is None or values["notas"] == {}:
                values["notas"] = None
        return values


class GeminiResponse(BaseModel):
    """Estructura completa de la respuesta de Gemini (versión simplificada)."""
    pacientes: list[PacienteExtraido] = []
    advertencias: list[str] = []


class ExtraccionRead(BaseModel):
    id: uuid.UUID
    paciente_id: uuid.UUID
    imagen_original: str
    modelo_vlm: str
    raw_output: dict
    conf_global: float | None
    es_completo: bool
    razon_parcial: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtraccionResult(BaseModel):
    """Respuesta tras procesar una imagen."""
    pacientes_creados: list[uuid.UUID] = []
    total_pacientes: int = 0
    advertencias: list[str] = []
    raw_respuesta: GeminiResponse | None = None
