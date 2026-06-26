## ADDED Requirements

### Requirement: El sistema debe buscar pacientes por cédula

El endpoint GET /api/v1/busqueda?cedula=X SHALL buscar pacientes cuya cédula coincida exactamente (índice exacto).

#### Scenario: Búsqueda por cédula exacta
- **WHEN** un usuario busca con `cedula=12345678` y existe un paciente con esa cédula
- **THEN** el sistema devuelve el paciente completo con todos sus campos

#### Scenario: Cédula no encontrada
- **WHEN** un usuario busca con `cedula=99999999` y no existe ningún paciente
- **THEN** el sistema devuelve HTTP 200 con `{ "encontrado": false, "mensaje": "No se encontró un paciente con esa cédula" }`

#### Scenario: Cédula con formato sucio
- **WHEN** un usuario busca con `cedula=V-12.345.678`
- **THEN** el sistema normaliza el input (elimina no dígitos) antes de buscar

### Requirement: El sistema debe buscar pacientes por nombre

El endpoint GET /api/v1/busqueda?nombre=X SHALL buscar pacientes cuyo nombre contenga el texto (ILIKE / case-insensitive).

#### Scenario: Búsqueda parcial por nombre
- **WHEN** un usuario busca con `nombre=María`
- **THEN** el sistema devuelve todos los pacientes cuyo nombre contenga "María" (insensible a mayúsculas)

#### Scenario: Nombre con acentos
- **WHEN** un usuario busca con `nombre=Perez` y existe "Pérez" en la base
- **THEN** el sistema devuelve el paciente (la búsqueda es insensible a acentos usando unicode normalization)

#### Scenario: Múltiples resultados
- **WHEN** un usuario busca con `nombre=José` y existen 5 pacientes con ese nombre
- **THEN** el sistema devuelve los 5 resultados paginados

### Requirement: El sistema debe hacer búsqueda global

El endpoint GET /api/v1/busqueda?q=X SHALL buscar tanto en cédula como en nombre simultáneamente.

#### Scenario: Búsqueda global
- **WHEN** un usuario busca con `q=1234`
- **THEN** el sistema busca pacientes cuya cédula contenga "1234" O cuyo nombre contenga "1234"

#### Scenario: Búsqueda global encuentra por cédula y nombre
- **WHEN** un usuario busca con `q=Maria` y existen pacientes con nombre "María" y pacientes con cédula que contiene "1234"
- **THEN** el sistema devuelve todos los resultados combinados

### Requirement: El sistema debe devolver resultados en formato consistente

Toda respuesta de búsqueda SHALL devolver `{ "encontrado": bool, "resultados": [...], "total": N, "mensaje": "..." }`.

#### Scenario: Respuesta con resultados
- **WHEN** la búsqueda encuentra pacientes
- **THEN** el sistema devuelve `encontrado: true`, `resultados: [array de pacientes]`, `total: N`, `mensaje: null`

#### Scenario: Respuesta sin resultados
- **WHEN** la búsqueda no encuentra pacientes
- **THEN** el sistema devuelve `encontrado: false`, `resultados: []`, `total: 0`, `mensaje: "No se encontraron pacientes que coincidan con la búsqueda"`
