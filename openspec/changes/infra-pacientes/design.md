## Context

Sistema para centralizar listados hospitalarios venezolanos durante emergencias. Voluntarios fotografían listados en hospitales, un VLM (Gemini) extrae los datos, y familiares consultan la información para localizar pacientes.

El sistema es 100% nuevo, sin legado. La infraestructura corre en Docker Compose. El frontend no está en el alcance de este diseño (se definirá separadamente).

Stack definido:
- **Backend**: Python 3.12+ / FastAPI
- **Base de datos**: PostgreSQL 16
- **VLM**: Google Gemini 2.0 Flash (API externa)
- **ORM**: SQLAlchemy 2.0 + asyncpg
- **Validación**: Pydantic v2
- **Infraestructura**: Docker Compose

## Goals / Non-Goals

**Goals:**
- Pipeline de extracción VLM que recibe imágenes y devuelve datos estructurados con niveles de confianza
- API REST para CRUD de pacientes, búsqueda y verificación comunitaria
- Separación automática entre registros completos y fragmentos parciales
- Almacenamiento del raw_output de Gemini para auditoría y reprocesamiento
- Sistema de verificación comunitaria con estados progresivos
- Docker Compose funcional (app + db listos con un comando)

**Non-Goals:**
- Frontend web (se implementará separadamente)
- Autenticación de usuarios (fase posterior)
- Búsqueda facial por foto del familiar (fase 2, requiere embeddings)
- Despliegue en producción (infraestructura cloud)
- Escalado horizontal
- Internacionalización (solo español por ahora)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      ARQUITECTURA GENERAL                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │          │    │                  │    │              │   │
│  │  Cliente │───▶│   FastAPI App    │───▶│  PostgreSQL  │   │
│  │  (HTTP)  │    │                  │    │              │   │
│  └──────────┘    │  ┌────────────┐  │    └──────────────┘   │
│                  │  │  Routers   │  │                       │
│                  │  │            │  │    ┌──────────────┐   │
│                  │  │• pacientes │  │    │              │   │
│                  │  │• extraccion│  │───▶│  Gemini API  │   │
│                  │  │• busqueda  │  │    │  (VLM)       │   │
│                  │  │• verificac │  │    └──────────────┘   │
│                  │  └─────┬──────┘  │                       │
│                  │        │         │    ┌──────────────┐   │
│                  │  ┌─────▼──────┐  │    │              │   │
│                  │  │  Services  │  │    │  Almacenam.  │   │
│                  │  │            │  │───▶│  imágenes    │   │
│                  │  │• gemini    │  │    │  (disco/S3)  │   │
│                  │  │• extraccion│  │    └──────────────┘   │
│                  │  │• busqueda  │  │                       │
│                  │  └────────────┘  │                       │
│                  └──────────────────┘                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Flujo de extracción

```
📸 POST /api/v1/extraccion/upload
       │
       ▼
┌──────────────────┐
│ 1. Validar imagen │ ← Formato, tamaño, tipo
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ 2. Guardar imagen │ ← disco local / volumen Docker
└──────┬───────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 3. Llamar Gemini 2.0 Flash          │
│    prompt refinado + imagen          │
│    temperature=0.1, max_tokens=4096  │
└──────────────┬──────────────────────┘
       │
       ▼
┌──────────────────┐
│ 4. Parsear JSON   │ ← Validar estructura Pydantic
└──────┬───────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 5. Separar completos vs parciales    │
│    ┌──────────┐   ┌───────────────┐  │
│    │completos │   │  parciales    │  │
│    │→ DB      │   │→ log + ignore │  │
│    └──────────┘   └───────────────┘  │
└──────────────┬──────────────────────┘
       │
       ▼
┌──────────────────┐
│ 6. Guardar en DB  │ ← pacientes + extracciones
└──────────────────┘
```

## Decisions

### 1. FastAPI sobre Flask / Django

| Criterio | FastAPI | Flask | Django |
|----------|---------|-------|--------|
| Rendimiento async | Nativo | Con extensiones | Complejo |
| Validación Pydantic | Nativo | Manual | DRF |
| Documentación OpenAPI | Auto | Con extensiones | DRF |
| Curva de aprendizaje | Baja | Baja | Alta |
| Peso del framework | Ligero | Ligero | Pesado |

**Decisión**: FastAPI. async nativo para llamadas a Gemini (IO-bound), Pydantic integrado, documentación automática.

### 2. SQLAlchemy async + asyncpg sobre psycopg2

FastAPI es async, el driver sync bloquearía el event loop. SQLAlchemy 2.0 async con asyncpg es el estándar actual.

### 3. Gemini 2.0 Flash sobre Gemini Pro o VLMs open-source

- Flash es más rápido y económico, ideal para alto volumen
- La calidad de extracción es suficiente con un prompt bien diseñado
- Si se necesita más precisión, se puede subir a Pro 1.5 como fallback
- Alternativas open-source (Qwen-VL, Llava) requieren GPU, no viable para MVP

### 4. Almacenamiento de imágenes en disco local (volumen Docker)

Para MVP, las imágenes se guardan en un volumen Docker. Configurable mediante variable de entorno para usar S3 en producción.

### 5. Dos tablas separadas: pacientes y extracciones

Cada intento de extracción se guarda como registro independiente en `extracciones`. Esto permite:
- Auditoría completa (qué dijo Gemini, cuándo, con qué imagen)
- Reprocesamiento si se mejora el prompt
- Comparar múltiples extracciones del mismo paciente
- La tabla `pacientes` almacena el mejor dato disponible

### 6. Sistema de verificación comunitaria sin usuarios registrados

En MVP no hay autenticación. Cualquier persona puede ver la imagen original y los datos extraídos, y hacer clic en "confirmar" o "reportar error". Se identifica por un hash del dispositivo/navegador (fingerprinting básico) para evitar voto múltiple, pero no es infalible —es un balance entre accesibilidad y precisión.

## Data Model

```sql
-- Tabla principal: pacientes
CREATE TABLE pacientes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          VARCHAR(300) NOT NULL,
    cedula          VARCHAR(10),        -- solo dígitos, indexado
    hospital        VARCHAR(300),
    piso            VARCHAR(20),
    habitacion      VARCHAR(20),
    estado_salud    TEXT,
    contacto        VARCHAR(20),        -- normalizado +58...
    foto_url        TEXT,               -- foto del familiar (futuro)
    status_verificacion VARCHAR(20) NOT NULL DEFAULT 'no_verificado'
                    CHECK (status_verificacion IN (
                        'no_verificado', 'parcial', 'verificado', 'error'
                    )),
    confianza_global    FLOAT,
    ultima_extraccion_id UUID,          -- FK a extracciones
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pacientes_cedula ON pacientes(cedula);
CREATE INDEX idx_pacientes_nombre ON pacientes(nombre varchar_pattern_ops);

-- Cada intento de VLM
CREATE TABLE extracciones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id     UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    imagen_original TEXT NOT NULL,           -- ruta/URL
    modelo_vlm      VARCHAR(50) NOT NULL DEFAULT 'gemini-2.0-flash',
    prompt_usado    TEXT,                   -- snapshot del prompt
    raw_output      JSONB NOT NULL,          -- respuesta completa de Gemini
    metadatos       JSONB,                  -- metadata de la imagen (dimensiones, etc)
    -- Confianzas por campo
    conf_nombre     FLOAT,
    conf_cedula     FLOAT,
    conf_hospital   FLOAT,
    conf_piso       FLOAT,
    conf_habitacion FLOAT,
    conf_estado     FLOAT,
    conf_contacto   FLOAT,
    conf_global     FLOAT,
    es_completo     BOOLEAN NOT NULL DEFAULT TRUE,
    razon_parcial   TEXT,                   -- si es parcial, por qué
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Verificaciones comunitarias
CREATE TABLE verificaciones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id     UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    verificador_id  VARCHAR(64) NOT NULL,   -- fingerprint del dispositivo
    tipo            VARCHAR(20) NOT NULL CHECK (tipo IN ('confirmar', 'reportar_error')),
    comentario      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(paciente_id, verificador_id)     -- 1 voto por persona por paciente
);
```

## API Endpoints

```
POST   /api/v1/extraccion/upload          # Subir imagen → extraer → guardar
GET    /api/v1/pacientes                  # Listar pacientes (paginado)
GET    /api/v1/pacientes/{id}             # Detalle de paciente
GET    /api/v1/pacientes/{id}/imagen      # Ver imagen original del listado
GET    /api/v1/pacientes/{id}/extracciones # Historial de extracciones
GET    /api/v1/busqueda?cedula=X          # Buscar por cédula
GET    /api/v1/busqueda?nombre=X          # Buscar por nombre
GET    /api/v1/busqueda?q=X              # Búsqueda global (cedula o nombre)
POST   /api/v1/verificaciones/{paciente_id}  # Votar (confirmar/reportar)
GET    /api/v1/verificaciones/{paciente_id}  # Ver votos del paciente
GET    /api/v1/estadisticas               # Stats: total pacientes, verificados, etc.
```

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app, startup, lifespan
│   ├── config.py                     # Settings (pydantic-settings)
│   ├── database.py                   # SQLAlchemy engine, session
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── paciente.py               # SQLAlchemy model: Paciente
│   │   ├── extraccion.py             # SQLAlchemy model: Extraccion
│   │   └── verificacion.py           # SQLAlchemy model: Verificacion
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── paciente.py               # Pydantic: PacienteCreate, PacienteRead, etc
│   │   ├── extraccion.py             # Pydantic: ExtraccionRead, ExtraccionResult
│   │   ├── busqueda.py               # Pydantic: BusquedaParams, BusquedaResult
│   │   └── verificacion.py           # Pydantic: VerificacionCreate, VerificacionRead
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── pacientes.py              # /api/v1/pacientes
│   │   ├── extraccion.py             # /api/v1/extraccion
│   │   ├── busqueda.py               # /api/v1/busqueda
│   │   └── verificaciones.py         # /api/v1/verificaciones
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py         # Llamada a Gemini API + prompt
│   │   ├── extraccion_service.py     # Orquestación: subida → VLM → parseo → DB
│   │   ├── pacientes_service.py      # CRUD lógica de pacientes
│   │   └── verificacion_service.py   # Lógica de verificación y estados
│   │
│   └── utils/
│       ├── __init__.py
│       └── imagen.py                 # Validación y preprocesamiento de imágenes
│
├── uploads/                          # Imágenes subidas (volumen Docker)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Risks / Trade-offs

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Gemini alucina datos** | Alto | Prompt diseñado para baja confianza ante incertidumbre; almacenar raw_output para auditoría; sistema de verificación comunitaria |
| **Costo de API Gemini** | Medio | Flash es económico (~$0.10/1K imágenes); configurable para usar Pro solo en casos específicos |
| **Imágenes de baja calidad** | Alto | Validación al subir (nitidez mínima); preprocesamiento (contraste, rotación); la confianza refleja la calidad |
| **Voto fraudulento** en verificación comunitaria | Bajo | Fingerprinting básico; un voto por persona por paciente; no es crítico para MVP |
| **Datos duplicados** (misma persona, múltiples fotos) | Medio | Búsqueda por cédula antes de insertar; si existe, agregar nueva extracción vinculada |
| **Privacidad de datos médicos** | Alto | Sin autenticación en MVP = datos públicos; documentar claramente; en producción agregar auth y HTTPS |

## Open Questions

1. ¿Se necesita autenticación desde el MVP o puede ser completamente abierto?
2. ¿Las imágenes originales deben tener algún tratamiento de privacidad (ej: blurring de datos sensibles no relevantes)?
3. ¿Face embeddings para búsqueda por foto se implementa en fase 1 o fase 2?
4. ¿Hosting: cloud (Render/Railway) o VPS propio?
