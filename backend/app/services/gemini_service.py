import json
import logging
import re
from pathlib import Path

import google.api_core.exceptions as google_exceptions
import google.generativeai as genai

from app.config import settings
from app.schemas.extraccion import GeminiResponse

logger = logging.getLogger(__name__)


class GeminiQuotaError(Exception):
    """Error por límite de cuota en Gemini API."""
    def __init__(self, message: str, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


class GeminiAuthError(Exception):
    """Error de autenticación con Gemini API (API key inválida o no configurada)."""
    pass

# ---------------------------------------------------------------------------
# PROMPT DE EXTRACCIÓN — Versión original detallada
# (funcionaba correctamente según pruebas)
# ---------------------------------------------------------------------------
PROMPT_EXTRACCION = """
Eres un extractor de datos de listados hospitalarios venezolanos.
Tu función es leer imágenes de listados de pacientes en hospitales
y extraer la información de CADA persona en la imagen con la MÁXIMA
precisión posible.

═══════════════════════════════════════════════════════════════
                      REGLAS ABSOLUTAS
═══════════════════════════════════════════════════════════════

1. NO ALUCINES. Si no estás seguro de un valor, confianza baja.
   Es preferible decir "no estoy seguro" a inventar.

2. CÉDULA DE IDENTIDAD: Es el campo más crítico.
   - Formato venezolano: puede aparecer como "V-12.345.678",
     "12.345.678", "CI 12.345.678", "C.I. 12.345.678"
   - Normaliza a: solo números (12345678)
   - Si no ves claramente TODOS los dígitos, confianza baja.
   - Si ves la cédula parcialmente, extrae lo que puedas
     y confianza baja.

3. NOMBRE COMPLETO: Nombres y apellidos.
   - Típico venezolano: Nombre + Apellido (pueden ser compuestos)
   - Si ves solo un nombre, así lo devuelves.

4. HOSPITAL: Puede ser nombre completo o siglas.
   - Ej: "CDI Los Chaguaramos", "Hospital Dr. Domingo Luciani",
     "Hosp. Militar", "CDI El Valle"
   - Conserva el nombre tal como aparece.

5. PISO Y HABITACIÓN: Pueden aparecer juntos o separados.
   - "Piso 3, Hab 312" o "3-312" o "P3 H312"
   - Sepáralos en piso y habitación.

6. EDAD: Puede aparecer como "45 años", "45a", "45".
   - Importante para identificar pacientes con mismo nombre.
   - Normaliza a solo el número (45).
   - Si ves "3 meses", déjalo como texto: "3 meses".

7. ESTADO DE SALUD: Altamente variable.
   - "Estable", "Grave", "Crítico", "Reservado", "Mejoría",
     "Sedado", "Intubado", "Quirófano", "Alta médica"
   - Texto libre: a veces describen condiciones específicas.
   - Consérvalo textual.

8. CONTACTO: Teléfono venezolano.
   - Formato: 0412-555-1234, +58 412 555 1234, (0412) 555-1234
   - Normaliza a: +58XXXXXXXXX (sin espacios ni guiones)
   - Pueden ser números de contacto del familiar.

═══════════════════════════════════════════════════════════════
                    FORMATO DE SALIDA
═══════════════════════════════════════════════════════════════

Devuelve un JSON con esta estructura EXACTA:

{
  "pacientes": [
    {
      "nombre": {
        "valor": "María José Pérez Rodríguez",
        "confianza": 0.95,
        "raw_text": "María Pérez"
      },
      "cedula": {
        "valor": "12345678",
        "confianza": 0.92,
        "raw_text": "V-12.345.678"
      },
      "hospital": {
        "valor": "CDI Los Chaguaramos",
        "confianza": 0.98,
        "raw_text": "CDI Los Chaguaramos"
      },
      "piso": {
        "valor": "3",
        "confianza": 0.99,
        "raw_text": "Piso 3"
      },
      "habitacion": {
        "valor": "312",
        "confianza": 0.99,
        "raw_text": "Hab 312"
      },
      "edad": {
        "valor": "45",
        "confianza": 0.95,
        "raw_text": "45 años"
      },
      "estado_salud": {
        "valor": "Estable",
        "confianza": 0.85,
        "raw_text": "estable"
      },
      "contacto": {
        "valor": "+584125551234",
        "confianza": 0.90,
        "raw_text": "0412-555-1234"
      },
      "notas": null
    }
  ],
  "advertencias": []
}

REGLAS DE CONFIANZA:
- 0.90 - 1.00 → SEGURO: Valor claramente legible, sin ambigüedad
- 0.70 - 0.89 → MODERADO: Legible pero con algún factor de duda
- 0.50 - 0.69 → BAJO: Parcialmente ilegible, hay que verificarlo
- 0.00 - 0.49 → INCIERTO: Mayormente ilegible, no confiar sin verificar
- null → NO ENCONTRADO: El campo no aparece en la imagen

═══════════════════════════════════════════════════════════════
                   EJEMPLO PRÁCTICO
═══════════════════════════════════════════════════════════════

IMAGEN: Un listado escrito a mano en una hoja de cuaderno que dice:
  "1. María Pérez C.I 12.345.678
      CDI Los Chaguaramos - Piso 3 Hab 312
      Estable - Contacto: 0412-555-1234
   2. José Daniel Medina, C.I 23.456.789
      Piso 3 Hab 315 - Grave - 0426-987-6543"

RESPUESTA ESPERADA:
{
  "pacientes": [
    {
      "nombre": { "valor": "María Pérez", "confianza": 0.95, "raw_text": "María Pérez" },
      "cedula": { "valor": "12345678", "confianza": 0.95, "raw_text": "C.I 12.345.678" },
      "hospital": { "valor": "CDI Los Chaguaramos", "confianza": 0.98, "raw_text": "CDI Los Chaguaramos" },
      "piso": { "valor": "3", "confianza": 0.99, "raw_text": "Piso 3" },
      "habitacion": { "valor": "312", "confianza": 0.99, "raw_text": "Hab 312" },
      "edad": { "valor": "45", "confianza": 0.95, "raw_text": "45 años" },
      "estado_salud": { "valor": "Estable", "confianza": 0.90, "raw_text": "Estable" },
      "contacto": { "valor": "+584125551234", "confianza": 0.95, "raw_text": "0412-555-1234" },
      "notas": null
    },
    {
      "nombre": { "valor": "José Daniel Medina", "confianza": 0.90, "raw_text": "José Daniel Medina" },
      "cedula": { "valor": "23456789", "confianza": 0.90, "raw_text": "C.I 23.456.789" },
      "hospital": { "valor": "CDI Los Chaguaramos", "confianza": 0.80, "raw_text": "inferido del encabezado del listado" },
      "piso": { "valor": "3", "confianza": 0.99, "raw_text": "Piso 3" },
      "habitacion": { "valor": "315", "confianza": 0.99, "raw_text": "Hab 315" },
      "edad": { "valor": "60", "confianza": 0.90, "raw_text": "60 años" },
      "estado_salud": { "valor": "Grave", "confianza": 0.90, "raw_text": "Grave" },
      "contacto": { "valor": "+584269876543", "confianza": 0.95, "raw_text": "0426-987-6543" },
      "notas": "El hospital inferido del encabezado del listado."
    }
  ],
  "advertencias": []
}

═══════════════════════════════════════════════════════════════
                  INSTRUCCIÓN FINAL
═══════════════════════════════════════════════════════════════

Extrae TODOS los pacientes visibles en la imagen.
NO te limites a unos pocos. Si hay 30 pacientes en el listado,
debes devolver los 30. No hagas "muestras" ni resúmenes.

Si un campo no está disponible para un paciente (ej: no tiene
cédula visible), devuelve el objeto CampoExtraido con valor null:
{"valor": null, "confianza": 0.0, "raw_text": ""}

Analiza la imagen ahora y devuelve SOLO el JSON.
"""


def _configurar_gemini() -> None:
    """Configurar el cliente de Gemini con la API key."""
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY no configurada. "
            "Establece la variable de entorno o créala en .env"
        )
    genai.configure(api_key=settings.gemini_api_key)


async def extraer_datos_desde_imagen(ruta_imagen: str) -> GeminiResponse:
    """
    Envía una imagen a Gemini 2.0 Flash y devuelve los datos extraídos
    estructurados según el schema GeminiResponse.

    Args:
        ruta_imagen: Ruta absoluta o relativa al archivo de imagen.

    Returns:
        GeminiResponse con pacientes_completos y pacientes_parciales.

    Raises:
        ValueError: Si la API key no está configurada.
        GeminiQuotaError: Si se excede la cuota de Gemini (429).
        GeminiAuthError: Si la API key es inválida.
        FileNotFoundError: Si la imagen no existe.
    """
    _configurar_gemini()

    imagen = Path(ruta_imagen)
    if not imagen.exists():
        raise FileNotFoundError(f"Imagen no encontrada: {ruta_imagen}")

    logger.info("Enviando imagen a Gemini: %s", ruta_imagen)

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        generation_config={
            "temperature": settings.gemini_temperature,
            "max_output_tokens": settings.gemini_max_tokens,
        },
    )

    # Subir archivo y generar contenido con manejo de errores
    uploaded = None
    try:
        uploaded = genai.upload_file(str(imagen))
        response = model.generate_content([PROMPT_EXTRACCION, uploaded])
    except google_exceptions.ResourceExhausted as exc:
        retry_seconds = _extraer_retry_delay(str(exc))
        logger.warning("Cuota de Gemini agotada. Reintentar en %s segundos.", retry_seconds)
        raise GeminiQuotaError(
            message=str(exc),
            retry_after_seconds=retry_seconds,
        ) from exc
    except google_exceptions.Unauthenticated as exc:
        raise GeminiAuthError(
            "API key de Gemini inválida. Verifica GEMINI_API_KEY en .env"
        ) from exc
    except google_exceptions.PermissionDenied as exc:
        raise GeminiAuthError(
            "API key de Gemini sin permisos. Verifica que la API key tenga acceso a Gemini API."
        ) from exc
    finally:
        # Limpiar archivo temporal en Gemini
        if uploaded:
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                logger.warning(
                    "No se pudo eliminar archivo temporal: %s", uploaded.name
                )

    return _parsear_respuesta(response.text)


def _extraer_retry_delay(mensaje_error: str) -> int | None:
    """
    Extrae el tiempo de reintento desde el mensaje de error de Gemini.

    Busca el patrón 'retry_delay { seconds: N }' en el texto del error.
    """
    match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", mensaje_error)
    if match:
        return int(match.group(1))
    # También busca 'retry in X.XXXs'
    match = re.search(r"retry in ([\d.]+)s", mensaje_error, re.IGNORECASE)
    if match:
        return int(float(match.group(1)))
    return None


def _parsear_respuesta(texto: str) -> GeminiResponse:
    """
    Parsea el texto JSON devuelto por Gemini y lo valida contra GeminiResponse.
    """
    # Limpiar posibles markdown fences ```json ... ```
    texto_limpio = texto.strip()
    if texto_limpio.startswith("```"):
        # Extraer contenido entre los delimitadores
        lineas = texto_limpio.splitlines()
        # Encontrar primera y última línea con ```
        inicio = 0
        fin = len(lineas)
        for i, linea in enumerate(lineas):
            if linea.strip().startswith("```"):
                if inicio == 0:
                    inicio = i + 1
                else:
                    fin = i
                    break
        texto_limpio = "\n".join(lineas[inicio:fin])

    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError as exc:
        logger.error("Respuesta de Gemini no es JSON válido: %s", exc)
        logger.debug("Texto recibido: %s", texto)
        raise ValueError(f"Error al parsear respuesta JSON de Gemini: {exc}") from exc

    try:
        return GeminiResponse(**datos)
    except Exception as exc:
        logger.error("Respuesta de Gemini no cumple el schema esperado: %s", exc)
        logger.debug("Datos recibidos: %s", datos)
        raise ValueError(f"Estructura de respuesta inválida: {exc}") from exc
