## ADDED Requirements

### Requirement: El sistema debe permitir confirmar datos de un paciente

Cualquier usuario SHALL poder enviar un voto de "confirmar" para un paciente, indicando que los datos extraídos coinciden con la imagen original.

#### Scenario: Confirmación exitosa
- **WHEN** un usuario envía POST /api/v1/verificaciones/{paciente_id} con `{ "tipo": "confirmar" }`
- **THEN** el sistema crea un registro en `verificaciones` con tipo `confirmar`

#### Scenario: Doble voto del mismo usuario
- **WHEN** el mismo verificador_id intenta votar dos veces sobre el mismo paciente
- **THEN** el sistema rechaza con error HTTP 409 y mensaje "Ya has votado sobre este paciente"

### Requirement: El sistema debe permitir reportar errores

Cualquier usuario SHALL poder reportar un error en los datos de un paciente, con comentario opcional.

#### Scenario: Reporte de error
- **WHEN** un usuario envía POST /api/v1/verificaciones/{paciente_id} con `{ "tipo": "reportar_error", "comentario": "La cédula dice 12345679, no 12345678" }`
- **THEN** el sistema crea el registro y cambia el `status_verificacion` del paciente a `error`

### Requirement: El sistema debe actualizar el estado de verificación según los votos

El `status_verificacion` de un paciente SHALL actualizarse automáticamente según estas reglas:
- 0 confirmaciones → `no_verificado`
- 1 confirmación → `parcial`
- 3+ confirmaciones → `verificado`
- Cualquier reporte de error → `error`

#### Scenario: Transición a verificado
- **WHEN** un paciente llega a 3 confirmaciones
- **THEN** el sistema actualiza `status_verificacion` a `verificado`

#### Scenario: Reporte revierte a parcial
- **WHEN** un paciente está `verificado` y alguien reporta un error
- **THEN** el sistema cambia `status_verificacion` a `error`

### Requirement: El sistema debe mostrar el estado de verificación en consultas

Toda respuesta de paciente SHALL incluir `status_verificacion` y `total_confirmaciones` y `total_reportes`.

#### Scenario: Detalle con conteo de votos
- **WHEN** un usuario consulta GET /api/v1/pacientes/{id}
- **THEN** la respuesta incluye `status_verificacion`, `total_confirmaciones: N`, `total_reportes: M`
