import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.paciente import PacienteDetail, PacienteList, PacienteRead
from app.schemas.respuesta import ErrorResponse
from app.services import pacientes_service

router = APIRouter(prefix="/api/v1/pacientes", tags=["Pacientes"])


@router.get("", response_model=PacienteList)
async def listar_pacientes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los pacientes con paginación."""
    return await pacientes_service.listar_pacientes(db, limit=limit, offset=offset)


@router.get(
    "/{paciente_id}",
    response_model=PacienteDetail,
    responses={404: {"model": ErrorResponse}},
)
async def obtener_paciente(
    paciente_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene el detalle completo de un paciente, incluyendo conteo de verificaciones."""
    paciente = await pacientes_service.obtener_paciente(db, paciente_id)
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Paciente no encontrado", "error_code": "NOT_FOUND"},
        )
    return paciente


@router.get(
    "/{paciente_id}/imagen",
    responses={404: {"model": ErrorResponse}},
)
async def obtener_imagen_paciente(
    paciente_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Devuelve la imagen original del listado de donde se extrajo al paciente."""
    ruta = await pacientes_service.ruta_imagen_paciente(db, paciente_id)
    if not ruta:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Imagen no encontrada para este paciente", "error_code": "NOT_FOUND"},
        )

    ruta_path = Path(ruta)
    if not ruta_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"detail": "El archivo de imagen no existe en el servidor", "error_code": "FILE_NOT_FOUND"},
        )

    return FileResponse(
        path=ruta_path,
        media_type="image/jpeg",
        filename=ruta_path.name,
    )


@router.get(
    "/{paciente_id}/extracciones",
    responses={404: {"model": ErrorResponse}},
)
async def obtener_extracciones(
    paciente_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene el historial de extracciones VLM de un paciente."""
    paciente = await pacientes_service.obtener_paciente(db, paciente_id)
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Paciente no encontrado", "error_code": "NOT_FOUND"},
        )

    extracciones = await pacientes_service.obtener_extracciones(db, paciente_id)
    return {"paciente_id": str(paciente_id), "extracciones": extracciones}
