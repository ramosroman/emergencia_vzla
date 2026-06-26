## ADDED Requirements

### Requirement: El sistema debe almacenar pacientes con todos los campos extraídos

Cada paciente SHALL tener: nombre, cédula, hospital, piso, habitación, estado_salud, contacto, status_verificacion, confianza_global, y referencia a la extracción original.

#### Scenario: Creación de paciente desde extracción
- **WHEN** Gemini extrae un paciente completo con todos los campos
- **THEN** el sistema crea un registro en `pacientes` con todos los campos poblados y `status_verificacion = 'no_verificado'`

#### Scenario: Paciente con campos faltantes
- **WHEN** Gemini extrae un paciente completo pero sin campo `contacto`
- **THEN** el sistema crea el paciente con `contacto = NULL` y los demás campos poblados

### Requirement: El sistema debe prevenir duplicados por cédula

Si ya existe un paciente con la misma cédula, el sistema SHALL agregar la nueva extracción al paciente existente en lugar de crear un duplicado.

#### Scenario: Misma cédula, nuevo listado
- **WHEN** una nueva extracción produce una cédula que ya existe en `pacientes`
- **THEN** el sistema crea una nueva `extraccion` vinculada al `paciente` existente y actualiza `updated_at`

#### Scenario: Cédula nula (paciente sin documento)
- **WHEN** Gemini extrae un paciente sin cédula (cedula = null)
- **THEN** el sistema crea un nuevo paciente sin verificar duplicados, usando el nombre como identificador único

### Requirement: El sistema debe listar pacientes con paginación

El endpoint GET /api/v1/pacientes SHALL soportar paginación con parámetros `limit` (default 20, max 100) y `offset`.

#### Scenario: Paginación básica
- **WHEN** un usuario solicita GET /api/v1/pacientes?limit=10&offset=0
- **THEN** el sistema devuelve los primeros 10 pacientes y metadatos de paginación (total, limit, offset)

### Requirement: El sistema debe mostrar detalle de paciente individual

El endpoint GET /api/v1/pacientes/{id} SHALL devolver todos los campos del paciente más la lista de extracciones asociadas.

#### Scenario: Consulta de detalle
- **WHEN** un usuario solicita GET /api/v1/pacientes/{id-valido}
- **THEN** el sistema devuelve el paciente con todos sus campos y un array `extracciones` con el historial
