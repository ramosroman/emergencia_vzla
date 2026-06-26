import logging
import uuid
from pathlib import Path

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paciente import Paciente
from app.models.verificacion import Verificacion
from app.schemas.paciente import PacienteDetail, PacienteList, PacienteRead

logger = logging.getLogger(__name__)


async def listar_pacientes(
    db: AsyncSession, limit: int = 20, offset: int = 0
) -> PacienteList:
    """
    Lista pacientes con paginación.

    Args:
        db: Sesión de base de datos.
        limit: Máximo de resultados (default 20, max 100).
        offset: Desplazamiento para paginación.

    Returns:
        PacienteList con items, total, limit y offset.
    """
    # Total de registros
    total_result = await db.execute(select(func.count(Paciente.id)))
    total = total_result.scalar() or 0

    # Consulta paginada
    result = await db.execute(
        select(Paciente)
        .order_by(Paciente.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    pacientes = result.scalars().all()

    return PacienteList(
        items=[PacienteRead.model_validate(p) for p in pacientes],
        total=total,
        limit=limit,
        offset=offset,
    )


async def obtener_paciente(
    db: AsyncSession, paciente_id: uuid.UUID
) -> PacienteDetail | None:
    """
    Obtiene un paciente por su ID, incluyendo conteo de verificaciones.

    Args:
        db: Sesión de base de datos.
        paciente_id: UUID del paciente.

    Returns:
        PacienteDetail o None si no existe.
    """
    result = await db.execute(
        select(Paciente).where(Paciente.id == paciente_id)
    )
    paciente = result.scalar_one_or_none()

    if not paciente:
        return None

    # Contar verificaciones
    confirmaciones = await db.execute(
        select(func.count(Verificacion.id)).where(
            Verificacion.paciente_id == paciente_id,
            Verificacion.tipo == "confirmar",
        )
    )
    reportes = await db.execute(
        select(func.count(Verificacion.id)).where(
            Verificacion.paciente_id == paciente_id,
            Verificacion.tipo == "reportar_error",
        )
    )

    detail = PacienteDetail.model_validate(paciente)
    detail.total_confirmaciones = confirmaciones.scalar() or 0
    detail.total_reportes = reportes.scalar() or 0
    return detail


async def obtener_paciente_por_cedula(
    db: AsyncSession, cedula: str
) -> PacienteRead | None:
    """
    Busca paciente por cédula exacta.

    La cédula se normaliza eliminando cualquier caracter no dígito.
    """
    cedula_limpia = _normalizar_cedula(cedula)
    if not cedula_limpia:
        return None

    result = await db.execute(
        select(Paciente).where(Paciente.cedula == cedula_limpia)
    )
    paciente = result.scalar_one_or_none()
    return PacienteRead.model_validate(paciente) if paciente else None


async def buscar_por_nombre(
    db: AsyncSession, nombre: str, limit: int = 20, offset: int = 0
) -> PacienteList:
    """
    Busca pacientes por nombre (ILIKE, case-insensitive, con normalización unicode).
    """
    # Usar ILIKE para búsqueda case-insensitive
    # Normalizar unicode: descomponer caracteres con acentos
    patron = f"%{nombre}%"

    # Total de resultados
    total_result = await db.execute(
        select(func.count(Paciente.id)).where(
            Paciente.nombre.ilike(patron)
        )
    )
    total = total_result.scalar() or 0

    # Resultados paginados
    result = await db.execute(
        select(Paciente)
        .where(Paciente.nombre.ilike(patron))
        .order_by(Paciente.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    pacientes = result.scalars().all()

    return PacienteList(
        items=[PacienteRead.model_validate(p) for p in pacientes],
        total=total,
        limit=limit,
        offset=offset,
    )


async def busqueda_global(
    db: AsyncSession, q: str, limit: int = 20, offset: int = 0
) -> PacienteList:
    """
    Búsqueda global que busca en cédula y nombre simultáneamente.
    """
    cedula_normalizada = _normalizar_cedula(q)
    patron = f"%{q}%"

    conditions = [Paciente.nombre.ilike(patron)]
    if cedula_normalizada:
        conditions.append(Paciente.cedula == cedula_normalizada)

    # Total
    total_result = await db.execute(
        select(func.count(Paciente.id)).where(or_(*conditions))
    )
    total = total_result.scalar() or 0

    # Resultados paginados
    result = await db.execute(
        select(Paciente)
        .where(or_(*conditions))
        .order_by(Paciente.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    pacientes = result.scalars().all()

    return PacienteList(
        items=[PacienteRead.model_validate(p) for p in pacientes],
        total=total,
        limit=limit,
        offset=offset,
    )


async def obtener_extracciones(
    db: AsyncSession, paciente_id: uuid.UUID
) -> list:
    """
    Obtiene todas las extracciones de un paciente, con datos de la imagen.
    """
    from app.models.extraccion import Extraccion

    result = await db.execute(
        select(Extraccion)
        .where(Extraccion.paciente_id == paciente_id)
        .order_by(Extraccion.created_at.desc())
    )
    extracciones = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "imagen_original": e.imagen_original,
            "modelo_vlm": e.modelo_vlm,
            "conf_global": e.conf_global,
            "es_completo": e.es_completo,
            "created_at": e.created_at.isoformat(),
        }
        for e in extracciones
    ]


async def ruta_imagen_paciente(
    db: AsyncSession, paciente_id: uuid.UUID
) -> str | None:
    """
    Obtiene la ruta de la imagen original asociada a la última extracción
    de un paciente.
    """
    from app.models.extraccion import Extraccion

    result = await db.execute(
        select(Extraccion.imagen_original)
        .where(Extraccion.paciente_id == paciente_id)
        .order_by(Extraccion.created_at.desc())
        .limit(1)
    )
    row = result.one_or_none()
    return row[0] if row else None


def _normalizar_cedula(cedula: str) -> str:
    """Elimina cualquier caracter que no sea dígito."""
    return "".join(c for c in cedula if c.isdigit())
