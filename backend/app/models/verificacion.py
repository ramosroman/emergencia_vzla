import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Verificacion(Base):
    __tablename__ = "verificaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pacientes.id", ondelete="CASCADE"),
        nullable=False,
    )
    verificador_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Relationships
    paciente = relationship("Paciente", back_populates="verificaciones")

    __table_args__ = (
        CheckConstraint(
            tipo.in_(["confirmar", "reportar_error"]), name="ck_verificacion_tipo"
        ),
        UniqueConstraint(
            "paciente_id", "verificador_id", name="uq_paciente_verificador"
        ),
    )

    def __repr__(self) -> str:
        return f"<Verificacion {self.tipo} - paciente {self.paciente_id}>"
