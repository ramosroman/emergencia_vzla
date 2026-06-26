## ADDED Requirements

### Requirement: El sistema debe exponer una API REST documentada con OpenAPI

FastAPI SHALL generar documentación interactiva en `/docs` (Swagger UI) y `/redoc`.

#### Scenario: Acceso a documentación
- **WHEN** un usuario navega a GET /docs
- **THEN** el sistema muestra Swagger UI con todos los endpoints documentados

### Requirement: El sistema debe correr en Docker Compose

El sistema SHALL incluir `docker-compose.yml` con servicios para `app` (FastAPI) y `db` (PostgreSQL 16).

#### Scenario: Inicio con Docker Compose
- **WHEN** un usuario ejecuta `docker compose up --build`
- **THEN** el sistema inicia PostgreSQL en puerto 5432 y la app FastAPI en puerto 8000

#### Scenario: Persistencia de datos
- **WHEN** el contenedor de PostgreSQL se reinicia
- **THEN** los datos persisten porque usan un volumen Docker nombrado

### Requirement: El sistema debe tener configuración mediante variables de entorno

La configuración SHALL manejarse con `pydantic-settings` y un archivo `.env`.

#### Scenario: Configuración por defecto
- **WHEN** no hay archivo `.env`
- **THEN** el sistema usa valores por defecto: DB en localhost:5432, uploads en ./uploads, sin API key de Gemini (devuelve error si se intenta extraer)

#### Scenario: Configuración personalizada
- **WHEN** existe un archivo `.env` con `GEMINI_API_KEY=xxx`, `DATABASE_URL=postgresql+asyncpg://...`
- **THEN** el sistema usa esos valores para conectarse

### Requirement: El sistema debe manejo de errores consistente

Toda respuesta de error SHALL devolver `{ "detail": "mensaje", "error_code": "codigo" }` con el código HTTP apropiado.

#### Scenario: Error 404
- **WHEN** un usuario solicita GET /api/v1/pacientes/{id-inexistente}
- **THEN** el sistema devuelve HTTP 404 con `{ "detail": "Paciente no encontrado", "error_code": "NOT_FOUND" }`

#### Scenario: Error 422 de validación
- **WHEN** un usuario envía un request con datos inválidos (ej: cédula con letras)
- **THEN** el sistema devuelve HTTP 422 con los detalles de validación de Pydantic

### Requirement: El sistema debe tener CORS habilitado para desarrollo

El middleware CORS SHALL permitir todos los orígenes en desarrollo (configurable por entorno).

#### Scenario: CORS permitido
- **WHEN** un frontend en localhost:5173 hace una petición
- **THEN** el sistema responde con headers CORS apropiados (Access-Control-Allow-Origin: *)
