import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Paciente(Base):
    __tablename__ = "pacientes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    cedula: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    hospital: Mapped[str | None] = mapped_column(String(300), nullable=True)
    piso: Mapped[str | None] = mapped_column(String(20), nullable=True)
    habitacion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado_salud: Mapped[str | None] = mapped_column(Text, nullable=True)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contacto: Mapped[str | None] = mapped_column(String(20), nullable=True)
    foto_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_verificacion: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="no_verificado",
    )
    confianza_global: Mapped[float | None] = mapped_column(Float, nullable=True)
    ultima_extraccion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    extracciones = relationship("Extraccion", back_populates="paciente")
    verificaciones = relationship("Verificacion", back_populates="paciente")

    __table_args__ = (
        CheckConstraint(
            status_verificacion.in_(
                ["no_verificado", "parcial", "verificado", "error"]
            ),
            name="ck_paciente_status_verificacion",
        ),
        Index("idx_pacientes_nombre", "nombre"),
    )

    def __repr__(self) -> str:
        return f"<Paciente {self.nombre} (CI: {self.cedula})>"
