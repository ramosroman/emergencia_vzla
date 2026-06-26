import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Extraccion(Base):
    __tablename__ = "extracciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False
    )
    imagen_original: Mapped[str] = mapped_column(Text, nullable=False)
    modelo_vlm: Mapped[str] = mapped_column(
        String(50), nullable=False, default="gemini-2.0-flash"
    )
    prompt_usado: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metadatos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Confianzas por campo
    conf_nombre: Mapped[float | None] = mapped_column(Float, nullable=True)
    conf_cedula: Mapped[float | None] = mapped_column(Float, nullable=True)
    conf_hospital: Mapped[float | None] = mapped_column(Float, nullable=True)
    conf_piso: Mapped[float | None] = mapped_column(Float, nullable=True)
    conf_habitacion: Mapped[float | None] = mapped_column(Float, nullable=True)
    conf_estado: Mapped[float | None] = mapped_column(Float, nullable=True)
    conf_contacto: Mapped[float | None] = mapped_column(Float, nullable=True)
    conf_global: Mapped[float | None] = mapped_column(Float, nullable=True)

    es_completo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    razon_parcial: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Relationships
    paciente = relationship("Paciente", back_populates="extracciones")

    def __repr__(self) -> str:
        return f"<Extraccion {self.id} - paciente {self.paciente_id}>"
