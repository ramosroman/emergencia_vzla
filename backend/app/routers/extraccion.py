import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.extraccion import ExtraccionResult
from app.schemas.respuesta import ErrorResponse
from app.services import extraccion_service
from app.services.gemini_service import GeminiAuthError, GeminiQuotaError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/extraccion", tags=["Extracción VLM"])


@router.post(
    "/upload",
    response_model=ExtraccionResult,
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"description": "Cuota de Gemini agotada"},
    },
)
async def upload_imagen(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """
    Sube una imagen de listado hospitalario para procesamiento VLM.

    La imagen se valida, se mejora su contraste, se envía a Gemini 2.0 Flash
    para extraer los datos, y se almacenan los pacientes encontrados en la base
    de datos.

    **Formatos aceptados:** JPEG, PNG, WEBP
    **Tamaño máximo:** 20MB

    **Nota sobre cuotas de Gemini:**
    Si recibes un error 429, la cuota gratuita se agotó. Puedes:
    1. Esperar a que se restablezca (usualmente 24h)
    2. Configurar un plan pago en https://ai.google.dev/pricing
    """
    if not file.filename:
        raise HTTPException(
            status_code=422,
            detail={"detail": "Nombre de archivo requerido", "error_code": "INVALID_FILE"},
        )

    contenido = await file.read()

    if len(contenido) == 0:
        raise HTTPException(
            status_code=422,
            detail={"detail": "El archivo está vacío", "error_code": "EMPTY_FILE"},
        )

    try:
        resultado = await extraccion_service.procesar_imagen(
            nombre_archivo=file.filename,
            contenido=contenido,
            db=db,
        )
        return resultado

    except GeminiQuotaError as exc:
        logger.warning("Cuota de Gemini agotada. Retry after: %s", exc.retry_after_seconds)
        headers = {}
        if exc.retry_after_seconds:
            headers["Retry-After"] = str(exc.retry_after_seconds)
        return JSONResponse(
            status_code=429,
            content={
                "detail": (
                    "Cuota de Gemini API agotada. "
                    "La cuota gratuita tiene límites diarios. "
                    "Espera unos minutos o configura un plan pago en https://ai.google.dev/pricing."
                ),
                "error_code": "GEMINI_QUOTA_EXCEEDED",
                "retry_after_seconds": exc.retry_after_seconds,
            },
            headers=headers,
        )

    except GeminiAuthError as exc:
        return JSONResponse(
            status_code=401,
            content={
                "detail": str(exc),
                "error_code": "GEMINI_AUTH_ERROR",
            },
        )

    except ValueError as exc:
        mensaje = str(exc)
        if "demasiado grande" in mensaje.lower():
            raise HTTPException(
                status_code=413,
                detail={"detail": mensaje, "error_code": "FILE_TOO_LARGE"},
            )
        if "formato no soportado" in mensaje.lower():
            raise HTTPException(
                status_code=415,
                detail={"detail": mensaje, "error_code": "UNSUPPORTED_FORMAT"},
            )
        raise HTTPException(
            status_code=422,
            detail={"detail": mensaje, "error_code": "VALIDATION_ERROR"},
        )

    except Exception as exc:
        logger.exception("Error inesperado procesando imagen")
        raise HTTPException(
            status_code=500,
            detail={"detail": f"Error interno del servidor: {str(exc)}", "error_code": "INTERNAL_ERROR"},
        )
