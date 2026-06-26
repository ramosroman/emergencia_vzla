import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.verificacion import Verificacion
from app.schemas.verificacion import VerificacionCreate, VerificacionRead, VerificacionStats

logger = logging.getLogger(__name__)

# Umbrales para cambio de estado
CONFIRMACIONES_PARA_PARCIAL = 1
CONFIRMACIONES_PARA_VERIFICADO = 3


async def registrar_voto(
    db: AsyncSession, paciente_id: uuid.UUID, voto: VerificacionCreate
) -> VerificacionStats:
    """
    Registra el voto de un verificador sobre un paciente.

    Reglas:
    - Un verificador solo puede votar una vez por paciente.
    - Si el voto es 'confirmar' y acumula 3+, el paciente pasa a 'verificado'.
    - Si el voto es 'reportar_error', el paciente pasa a 'error'.
    - Si hay 1 confirmación, el paciente pasa a 'parcial'.

    Args:
        db: Sesión de base de datos.
        paciente_id: UUID del paciente.
        voto: Datos del voto (tipo, verificador_id, comentario).

    Returns:
        VerificacionStats con estado actualizado.

    Raises:
        ValueError: Si el paciente no existe.
        ValueError: Si el verificador ya votó.
    """
    # Verificar que el paciente existe
    result = await db.execute(select(Paciente).where(Paciente.id == paciente_id))
    paciente = result.scalar_one_or_none()
    if not paciente:
        raise ValueError("Paciente no encontrado")

    # Verificar que el verificador no haya votado ya
    result = await db.execute(
        select(Verificacion).where(
            Verificacion.paciente_id == paciente_id,
            Verificacion.verificador_id == voto.verificador_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Ya has votado sobre este paciente")

    # Registrar voto
    nuevo_voto = Verificacion(
        paciente_id=paciente_id,
        verificador_id=voto.verificador_id,
        tipo=voto.tipo,
        comentario=voto.comentario,
    )
    db.add(nuevo_voto)
    await db.flush()

    # Actualizar estado del paciente
    await _actualizar_estado_paciente(db, paciente_id)

    # Devolver stats actualizados
    return await obtener_stats(db, paciente_id)


async def _actualizar_estado_paciente(db: AsyncSession, paciente_id: uuid.UUID) -> None:
    """
    Actualiza el status_verificacion del paciente según las reglas:
    - 0 confirmaciones → no_verificado
    - 1+ confirmaciones → parcial
    - 3+ confirmaciones → verificado
    - Cualquier reporte de error → error
    """
    # Contar confirmaciones
    result = await db.execute(
        select(func.count(Verificacion.id)).where(
            Verificacion.paciente_id == paciente_id,
            Verificacion.tipo == "confirmar",
        )
    )
    total_confirmaciones = result.scalar() or 0

    # Contar reportes de error
    result = await db.execute(
        select(func.count(Verificacion.id)).where(
            Verificacion.paciente_id == paciente_id,
            Verificacion.tipo == "reportar_error",
        )
    )
    total_reportes = result.scalar() or 0

    # Determinar nuevo estado
    if total_reportes > 0:
        nuevo_estado = "error"
    elif total_confirmaciones >= CONFIRMACIONES_PARA_VERIFICADO:
        nuevo_estado = "verificado"
    elif total_confirmaciones >= CONFIRMACIONES_PARA_PARCIAL:
        nuevo_estado = "parcial"
    else:
        nuevo_estado = "no_verificado"

    # Actualizar paciente
    result = await db.execute(select(Paciente).where(Paciente.id == paciente_id))
    paciente = result.scalar_one_or_none()
    if paciente:
        paciente.status_verificacion = nuevo_estado
        await db.flush()
        logger.info(
            "Paciente %s actualizado a estado: %s (confirmaciones: %d, reportes: %d)",
            paciente_id, nuevo_estado, total_confirmaciones, total_reportes,
        )


async def obtener_votos(
    db: AsyncSession, paciente_id: uuid.UUID
) -> list[VerificacionRead]:
    """
    Obtiene todos los votos de un paciente.
    """
    result = await db.execute(
        select(Verificacion)
        .where(Verificacion.paciente_id == paciente_id)
        .order_by(Verificacion.created_at.desc())
    )
    votos = result.scalars().all()
    return [VerificacionRead.model_validate(v) for v in votos]


async def obtener_stats(
    db: AsyncSession, paciente_id: uuid.UUID
) -> VerificacionStats:
    """
    Obtiene estadísticas de verificación de un paciente.
    """
    # Obtener paciente (para status)
    result = await db.execute(select(Paciente).where(Paciente.id == paciente_id))
    paciente = result.scalar_one_or_none()
    if not paciente:
        raise ValueError("Paciente no encontrado")

    # Contar confirmaciones
    result = await db.execute(
        select(func.count(Verificacion.id)).where(
            Verificacion.paciente_id == paciente_id,
            Verificacion.tipo == "confirmar",
        )
    )
    total_confirmaciones = result.scalar() or 0

    # Contar reportes
    result = await db.execute(
        select(func.count(Verificacion.id)).where(
            Verificacion.paciente_id == paciente_id,
            Verificacion.tipo == "reportar_error",
        )
    )
    total_reportes = result.scalar() or 0

    return VerificacionStats(
        paciente_id=paciente_id,
        status_verificacion=paciente.status_verificacion,
        total_confirmaciones=total_confirmaciones,
        total_reportes=total_reportes,
    )
