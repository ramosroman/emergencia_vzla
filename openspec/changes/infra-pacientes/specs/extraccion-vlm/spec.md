## ADDED Requirements

### Requirement: El sistema debe aceptar imágenes de listados hospitalarios

El sistema SHALL aceptar imágenes en formato JPEG, PNG y WEBP con un tamaño máximo de 20MB.

#### Scenario: Subida exitosa
- **WHEN** un usuario envía una imagen JPEG de 5MB con un listado hospitalario
- **THEN** el sistema acepta la imagen y la almacena en disco

#### Scenario: Imagen demasiado grande
- **WHEN** un usuario envía una imagen de 25MB
- **THEN** el sistema rechaza la imagen con error HTTP 413 y mensaje "Imagen demasiado grande. Máximo 20MB."

#### Scenario: Formato no soportado
- **WHEN** un usuario envía un archivo GIF
- **THEN** el sistema rechaza con error HTTP 415 y mensaje "Formato no soportado. Use JPEG, PNG o WEBP."

### Requirement: El sistema debe extraer datos usando Gemini 2.0 Flash

El sistema SHALL enviar la imagen a Gemini 2.0 Flash con el prompt refinado (versión con separación completos/parciales) y procesar la respuesta JSON.

#### Scenario: Extracción exitosa de paciente completo
- **WHEN** Gemini devuelve un JSON válido con un paciente en `pacientes_completos`
- **THEN** el sistema crea un registro en `pacientes` y un registro en `extracciones` con el raw_output completo

#### Scenario: Detección de fragmento parcial
- **WHEN** Gemini devuelve un JSON con entradas en `pacientes_parciales`
- **THEN** el sistema NO crea registros de paciente para esas entradas, pero guarda el raw_output completo en un log de auditoría

#### Scenario: Error de parseo JSON
- **WHEN** Gemini devuelve una respuesta que no es JSON válido
- **THEN** el sistema guarda el raw_output, no crea pacientes, y devuelve error HTTP 422 con mensaje "Error al procesar la respuesta del VLM"

### Requirement: El sistema debe almacenar niveles de confianza por campo

Cada campo extraído SHALL tener un nivel de confianza entre 0.0 y 1.0, almacenado en la tabla `extracciones`.

#### Scenario: Campos con confianza alta
- **WHEN** Gemini devuelve confianza >= 0.90 para todos los campos
- **THEN** el sistema almacena las confianzas y el paciente se marca con `confianza_global` en la tabla pacientes

#### Scenario: Campo con confianza baja
- **WHEN** Gemini devuelve confianza < 0.50 para la cédula
- **THEN** el sistema almacena el paciente igualmente, pero el campo `status_verificacion` se establece como `no_verificado`

### Requirement: El sistema debe permitir consultar la imagen original

Cada extracción SHALL estar vinculada a la imagen original que se usó para la extracción, almacenada en disco o S3.

#### Scenario: Consulta de imagen original
- **WHEN** un usuario solicita GET /api/v1/pacientes/{id}/imagen
- **THEN** el sistema retorna la imagen original del listado de donde se extrajo al paciente

### Requirement: El sistema debe devolver los datos extraídos al usuario tras la subida

Después de procesar una imagen, el sistema SHALL devolver una respuesta con los pacientes extraídos (completos) y la lista de fragmentos ignorados (parciales).

#### Scenario: Respuesta post-extracción
- **WHEN** un usuario sube una imagen y el procesamiento termina
- **THEN** el sistema devuelve un JSON con `pacientes_creados: [lista de IDs]`, `total_completos: N`, `total_parciales: M`, y `advertencias: [...]`
