import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.extraccion import Extraccion
from app.models.paciente import Paciente
from app.schemas.extraccion import (
    ExtraccionResult,
    GeminiResponse,
    PacienteExtraido,
)
from app.services.gemini_service import extraer_datos_desde_imagen
from app.utils.imagen import mejorar_contraste, validar_imagen

logger = logging.getLogger(__name__)


def guardar_imagen_en_disco(contenido: bytes, nombre_original: str) -> str:
    """
    Guarda la imagen subida en el directorio de uploads.

    Args:
        contenido: Contenido binario de la imagen.
        nombre_original: Nombre original del archivo.

    Returns:
        Ruta absoluta al archivo guardado.
    """
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generar nombre único para evitar colisiones
    ext = Path(nombre_original).suffix
    nombre_unico = f"{uuid.uuid4().hex}{ext}"
    ruta = upload_dir / nombre_unico

    with open(ruta, "wb") as f:
        f.write(contenido)

    logger.info("Imagen guardada: %s", ruta)
    return str(ruta.resolve())


async def procesar_imagen(
    nombre_archivo: str, contenido: bytes, db: AsyncSession
) -> ExtraccionResult:
    """
    Procesa una imagen de listado hospitalario:
    1. Valida la imagen
    2. Guarda en disco
    3. Mejora contraste
    4. Envía a Gemini
    5. Parsea respuesta
    6. Separa completos/parciales
    7. Guarda en DB
    8. Devuelve resultado

    Args:
        nombre_archivo: Nombre del archivo subido.
        contenido: Contenido binario.
        db: Sesión de base de datos.

    Returns:
        ExtraccionResult con los resultados del procesamiento.
    """
    # 1. Validar
    validar_imagen(nombre_archivo, contenido)

    # 2. Guardar imagen original en disco
    ruta_original = guardar_imagen_en_disco(contenido, nombre_archivo)

    # 3. Mejorar contraste (crear versión mejorada)
    ruta_mejorada = mejorar_contraste(ruta_original)

    # 4. Enviar a Gemini
    try:
        respuesta_gemini: GeminiResponse = await extraer_datos_desde_imagen(
            ruta_mejorada
        )
    except Exception as exc:
        logger.error("Error en extracción Gemini: %s", exc)
        raise

    # Guardar pacientes en DB
    pacientes_ids: list[uuid.UUID] = []
    for paciente_data in respuesta_gemini.pacientes:
        paciente_id = await _guardar_paciente_y_extraccion(
            db=db,
            paciente_data=paciente_data,
            ruta_imagen=ruta_original,
            respuesta_gemini=respuesta_gemini,
        )
        pacientes_ids.append(paciente_id)

    # Construir respuesta
    return ExtraccionResult(
        pacientes_creados=pacientes_ids,
        total_pacientes=len(respuesta_gemini.pacientes),
        advertencias=respuesta_gemini.advertencias,
        raw_respuesta=respuesta_gemini,
    )


async def _guardar_paciente_y_extraccion(
    db: AsyncSession,
    paciente_data: PacienteExtraido,
    ruta_imagen: str,
    respuesta_gemini,
) -> uuid.UUID:
    """
    Guarda o actualiza un paciente y crea su registro de extracción.

    Si ya existe un paciente con la misma cédula, vincula la extracción
    al paciente existente (evita duplicados).
    """
    cedula = paciente_data.cedula.valor
    hospital = paciente_data.hospital.valor
    edad = _parsear_edad(paciente_data.edad.valor)

    # Buscar si ya existe paciente con esa cédula
    paciente = None
    if cedula:
        result = await db.execute(
            select(Paciente).where(Paciente.cedula == cedula)
        )
        paciente = result.scalar_one_or_none()

    if paciente:
        logger.info("Paciente existente encontrado (cédula %s), vinculando nueva extracción", cedula)
    else:
        # Crear nuevo paciente
        paciente = Paciente(
            nombre=paciente_data.nombre.valor or "S/N",
            cedula=cedula,
            hospital=hospital,
            piso=paciente_data.piso.valor,
            habitacion=paciente_data.habitacion.valor,
            edad=edad,
            estado_salud=paciente_data.estado_salud.valor,
            contacto=paciente_data.contacto.valor,
            status_verificacion="no_verificado",
        )
        db.add(paciente)
        await db.flush()
        logger.info("Nuevo paciente creado: %s (cédula: %s)", paciente.nombre, cedula)

    # Crear extracción
    extraccion = Extraccion(
        paciente_id=paciente.id,
        imagen_original=ruta_imagen,
        modelo_vlm=settings.gemini_model,
        raw_output=respuesta_gemini.model_dump(mode="json"),
        conf_nombre=paciente_data.nombre.confianza,
        conf_cedula=paciente_data.cedula.confianza,
        conf_hospital=paciente_data.hospital.confianza,
        conf_piso=paciente_data.piso.confianza,
        conf_habitacion=paciente_data.habitacion.confianza,
        conf_estado=paciente_data.estado_salud.confianza,
        conf_contacto=paciente_data.contacto.confianza,
        conf_global=sum(
            c for c in [
                paciente_data.nombre.confianza,
                paciente_data.cedula.confianza,
                paciente_data.hospital.confianza,
                paciente_data.piso.confianza,
                paciente_data.habitacion.confianza,
                paciente_data.estado_salud.confianza,
                paciente_data.contacto.confianza,
            ] if c is not None
        ) / 7 if any(
            c is not None for c in [
                paciente_data.nombre.confianza,
                paciente_data.cedula.confianza,
                paciente_data.hospital.confianza,
                paciente_data.piso.confianza,
                paciente_data.habitacion.confianza,
                paciente_data.estado_salud.confianza,
                paciente_data.contacto.confianza,
            ]
        ) else None,
        es_completo=True,
    )
    db.add(extraccion)
    await db.flush()

    # Actualizar referencia en paciente
    paciente.ultima_extraccion_id = extraccion.id
    paciente.confianza_global = extraccion.conf_global
    await db.flush()

    return paciente.id


def _parsear_edad(valor: str | None) -> int | None:
    """
    Parsea la edad desde el texto extraído por Gemini.

    Gemini devuelve "45", "45 años", "45a", "3 meses", etc.
    Extrae el primer número encontrado.
    """
    if not valor:
        return None
    import re
    match = re.search(r"(\d+)", valor)
    if match:
        return int(match.group(1))
    return None
