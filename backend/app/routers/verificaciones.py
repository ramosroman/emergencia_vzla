import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.respuesta import ErrorResponse, SuccessResponse
from app.schemas.verificacion import VerificacionCreate, VerificacionRead, VerificacionStats
from app.services import verificacion_service

router = APIRouter(prefix="/api/v1/verificaciones", tags=["Verificación Comunitaria"])


@router.post(
    "/{paciente_id}",
    response_model=VerificacionStats,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def registrar_voto(
    paciente_id: uuid.UUID,
    voto: VerificacionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra un voto de verificación sobre un paciente.

    - **confirmar**: Los datos del paciente coinciden con la imagen original
    - **reportar_error**: Hay errores en los datos extraídos (requiere comentario)

    Cada persona solo puede votar una vez por paciente (identificado por verificador_id).
    """
    try:
        stats = await verificacion_service.registrar_voto(
            db=db,
            paciente_id=paciente_id,
            voto=voto,
        )
        return stats
    except ValueError as exc:
        mensaje = str(exc)
        if "no encontrado" in mensaje.lower():
            raise HTTPException(
                status_code=404,
                detail={"detail": mensaje, "error_code": "NOT_FOUND"},
            )
        if "ya has votado" in mensaje.lower():
            raise HTTPException(
                status_code=409,
                detail={"detail": mensaje, "error_code": "ALREADY_VOTED"},
            )
        raise HTTPException(
            status_code=422,
            detail={"detail": mensaje, "error_code": "VALIDATION_ERROR"},
        )


@router.get(
    "/{paciente_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
)
async def obtener_verificaciones(
    paciente_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene todos los votos y estadísticas de verificación de un paciente."""
    try:
        stats = await verificacion_service.obtener_stats(db, paciente_id)
        votos = await verificacion_service.obtener_votos(db, paciente_id)
        return {
            "stats": stats.model_dump(),
            "votos": [v.model_dump() for v in votos],
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"detail": str(exc), "error_code": "NOT_FOUND"},
        )
