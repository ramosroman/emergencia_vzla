# Emergencia Venezuela - Pacientes API

API para centralizar listados hospitalarios venezolanos durante emergencias. Voluntarios fotografían listados en hospitales, un modelo de visión por lenguaje (Gemini 3.1 Flash) extrae los datos estructurados, y familiares pueden buscar pacientes por cédula o nombre desde cualquier lugar.

## Stack

- **Backend**: Python 3.12+ / FastAPI
- **Base de datos**: PostgreSQL 16
- **VLM**: Google Gemini 3.1 Flash (API externa)
- **ORM**: SQLAlchemy 2.0 + asyncpg
- **Validacion**: Pydantic v2
- **Infraestructura**: Docker Compose

## Arquitectura

```
Cliente HTTP ──> FastAPI App ──> PostgreSQL
                     │
                     └──> Gemini API (VLM)
```

La aplicacion expone endpoints REST documentados automaticamente via OpenAPI en `/docs`.

### Flujo de extraccion

1. Subir foto del listado hospitalario (`POST /api/v1/extraccion/upload`)
2. Validacion y preprocesamiento de la imagen
3. Envio a Gemini 2.0 Flash con un prompt especializado
4. Parseo de la respuesta JSON estructurada
5. Almacenamiento en base de datos (paciente + extraccion)
6. Consulta disponible via busqueda

### Modelo de datos

- **Pacientes**: datos principales (nombre, cedula, hospital, piso, habitacion, estado_salud, contacto, edad) con nivel de confianza global y estado de verificacion
- **Extracciones**: cada intento de VLM se guarda como registro independiente para auditoria y reprocesamiento (incluye raw_output completo de Gemini)
- **Verificaciones**: votacion comunitaria donde cualquier persona puede confirmar o reportar errores en los datos extraidos

### Estados de verificacion

- `no_verificado` -- dato recien extraido, sin votos
- `parcial` -- al menos 1 confirmacion
- `verificado` -- 3 o mas confirmaciones
- `error` -- reportado como erroneo

## Requisitos

- Docker y Docker Compose
- Una API key de Google Gemini (gratuita en [Google AI Studio](https://aistudio.google.com/))

## Inicio rapido

### 1. Clonar y configurar

```bash
git clone https://github.com/ramosroman/emergencia_vzla.git
cd emergencia_vzla/backend
cp .env.example .env
```

### 2. Configurar variables de entorno

Editar `backend/.env`:

```env
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-2.0-flash
DATABASE_URL=postgresql+asyncpg://app:app_secret_123@localhost:5432/pacientes
UPLOAD_DIR=./uploads
CORS_ORIGINS=*
```

### 3. Iniciar servicios

```bash
docker compose up --build
```

Esto levanta:
- **PostgreSQL 16** en `localhost:5432`
- **API** en `localhost:8000`

### 4. Probar

```bash
# Verificar que la API responde
curl http://localhost:8000/health

# Subir una imagen de listado hospitalario
curl -X POST http://localhost:8000/api/v1/extraccion/upload \
  -F "imagen=@ruta/a/la/foto.jpg"

# Buscar pacientes
curl "http://localhost:8000/api/v1/busqueda?cedula=12345678"
curl "http://localhost:8000/api/v1/busqueda?nombre=Juan"
curl "http://localhost:8000/api/v1/busqueda?q=12345678"

# Ver documentacion interactiva
Abrir http://localhost:8000/docs
```

## API Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/api/v1/extraccion/upload` | Subir imagen de listado para extraccion VLM |
| `GET` | `/api/v1/pacientes` | Listar pacientes (paginado) |
| `GET` | `/api/v1/pacientes/{id}` | Detalle de paciente |
| `GET` | `/api/v1/pacientes/{id}/imagen` | Ver imagen original del listado |
| `GET` | `/api/v1/pacientes/{id}/extracciones` | Historial de extracciones del paciente |
| `GET` | `/api/v1/busqueda?cedula=X` | Buscar por cedula |
| `GET` | `/api/v1/busqueda?nombre=X` | Buscar por nombre |
| `GET` | `/api/v1/busqueda?q=X` | Busqueda global (cedula o nombre) |
| `POST` | `/api/v1/verificaciones/{id}` | Votar (confirmar o reportar error) |
| `GET` | `/api/v1/verificaciones/{id}` | Ver votos de un paciente |

## Estructura del proyecto

```
backend/
  app/
    main.py           # FastAPI app, startup, lifespan
    config.py         # Settings (pydantic-settings)
    database.py       # SQLAlchemy engine, session factory
    models/           # SQLAlchemy models (Paciente, Extraccion, Verificacion)
    schemas/          # Pydantic schemas (validacion request/response)
    routers/          # FastAPI routers (pacientes, extraccion, busqueda, verificaciones)
    services/         # Logica de negocio (gemini, extraccion, pacientes, verificacion)
    utils/            # Utilidades (validacion de imagenes)
  uploads/            # Imagenes subidas (volumen Docker)
  docker-compose.yml
  Dockerfile
  requirements.txt
  .env.example
```

## Licencia

MIT
