import logging
from pathlib import Path

from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

# Formatos permitidos
FORMATOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}

# Tamaño máximo en bytes
MAX_UPLOAD_SIZE = settings.max_upload_size_mb * 1024 * 1024


def validar_imagen(nombre_archivo: str, contenido: bytes) -> None:
    """
    Valida que el archivo sea una imagen con formato y tamaño permitidos.

    Args:
        nombre_archivo: Nombre del archivo (para detectar extensión).
        contenido: Contenido binario del archivo.

    Raises:
        ValueError: Si el formato o tamaño no son válidos.
    """
    # Validar tamaño
    if len(contenido) > MAX_UPLOAD_SIZE:
        raise ValueError(
            f"Imagen demasiado grande. Máximo {settings.max_upload_size_mb}MB. "
            f"Recibido: {len(contenido) / 1024 / 1024:.1f}MB"
        )

    # Validar extensión
    ext = Path(nombre_archivo).suffix.lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ValueError(
            f"Formato no soportado: '{ext}'. "
            f"Use: {', '.join(EXTENSIONES_PERMITIDAS)}"
        )

    # Validar que se pueda abrir como imagen
    try:
        img = Image.open(__import__("io").BytesIO(contenido))
        img.verify()
    except Exception as exc:
        raise ValueError(f"El archivo no es una imagen válida: {exc}") from exc


def mejorar_contraste(ruta_origen: str, ruta_destino: str | None = None) -> str:
    """
    Mejora el contraste de una imagen (útil para fotos oscuras de listados).

    Args:
        ruta_origen: Ruta a la imagen original.
        ruta_destino: Ruta para guardar la imagen mejorada. Si es None, sobreescribe.

    Returns:
        Ruta de la imagen procesada.
    """
    destino = ruta_destino or ruta_origen
    with Image.open(ruta_origen) as img:
        if img.mode != "L":
            img = img.convert("L")  # Convertir a escala de grises
        # Ecualización de histograma para mejorar contraste
        from PIL import ImageOps

        img_ecualizada = ImageOps.equalize(img)
        img_ecualizada.save(destino, quality=95)
    logger.info("Contraste mejorado: %s -> %s", ruta_origen, destino)
    return destino
