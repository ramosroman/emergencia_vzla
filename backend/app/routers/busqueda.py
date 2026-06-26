from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.busqueda import BusquedaResult
from app.services import pacientes_service

router = APIRouter(prefix="/api/v1/busqueda", tags=["Búsqueda"])


@router.get("", response_model=BusquedaResult)
async def buscar_pacientes(
    cedula: str | None = Query(None, description="Cédula exacta (solo dígitos)"),
    nombre: str | None = Query(None, description="Nombre o fragmento"),
    q: str | None = Query(None, description="Búsqueda global (cédula o nombre)"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca pacientes por cédula, nombre o búsqueda global.

    - **cedula**: Búsqueda exacta por cédula (se normaliza automáticamente)
    - **nombre**: Búsqueda parcial por nombre (insensible a mayúsculas)
    - **q**: Búsqueda global que busca en cédula y nombre simultáneamente

    Solo uno de los parámetros debe usarse a la vez.
    """
    if cedula:
        paciente = await pacientes_service.obtener_paciente_por_cedula(db, cedula)
        if paciente:
            return BusquedaResult(
                encontrado=True,
                resultados=[paciente],
                total=1,
            )
        return BusquedaResult(
            encontrado=False,
            resultados=[],
            total=0,
            mensaje="No se encontró un paciente con esa cédula",
        )

    if nombre:
        resultado = await pacientes_service.buscar_por_nombre(
            db, nombre, limit=limit, offset=offset
        )
        if resultado.total > 0:
            return BusquedaResult(
                encontrado=True,
                resultados=resultado.items,
                total=resultado.total,
            )
        return BusquedaResult(
            encontrado=False,
            resultados=[],
            total=0,
            mensaje="No se encontraron pacientes con ese nombre",
        )

    if q:
        resultado = await pacientes_service.busqueda_global(
            db, q, limit=limit, offset=offset
        )
        if resultado.total > 0:
            return BusquedaResult(
                encontrado=True,
                resultados=resultado.items,
                total=resultado.total,
            )
        return BusquedaResult(
            encontrado=False,
            resultados=[],
            total=0,
            mensaje="No se encontraron pacientes que coincidan con la búsqueda",
        )

    # Si no se proporciona ningún parámetro
    return BusquedaResult(
        encontrado=False,
        resultados=[],
        total=0,
        mensaje="Debes proporcionar al menos un parámetro de búsqueda: cedula, nombre o q",
    )
