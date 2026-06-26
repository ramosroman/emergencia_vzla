## Why

En Venezuela, durante emergencias humanitarias, los pacientes ingresan a hospitales sin que sus familias puedan localizarlos. Los listados hospitalarios existen en papel pero no hay un sistema centralizado de consulta. Esta aplicación permite que cualquier voluntario en un hospital fotografie los listados, un VLM (Gemini) extraiga los datos estructurados, y los familiares puedan buscar pacientes por cédula, nombre o foto del familiar desde cualquier lugar del país.

## What Changes

- **Backend FastAPI** con PostgreSQL para almacenamiento de pacientes y metadatos de extracción
- **Pipeline de extracción VLM** usando Gemini 2.0 Flash para leer listados hospitalarios y extraer: nombre, cédula, hospital, piso, habitación, estado de salud, contacto
- **API REST** con endpoints para:
  - Subir imagen de listado → extracción automática → almacenamiento
  - Búsqueda de pacientes por cédula, nombre
  - Búsqueda por foto del familiar (face embedding)
  - Verificación comunitaria de datos (confirmar/reportar errores)
  - Consulta de imagen original asociada a un registro
- **Sistema de confianza por campo** con niveles de 0.0 a 1.0, almacenando el raw_output completo de Gemini para auditoría
- **Separación automática** de registros completos vs parciales/fragmentos en la extracción
- **Sistema de verificación comunitaria** donde cualquier usuario puede confirmar o reportar errores en los datos extraídos
- **Docker Compose** para orquestar PostgreSQL + app

## Capabilities

### New Capabilities
- `extraccion-vlm`: Pipeline de subida de imágenes, procesamiento con Gemini 2.0 Flash, extracción estructurada con niveles de confianza, separación completos/parciales
- `gestion-pacientes`: CRUD de pacientes, almacenamiento de metadatos de extracción, asociación con imagen original
- `busqueda-pacientes`: Búsqueda por cédula, nombre, y foto del familiar (face embeddings)
- `verificacion-comunitaria`: Sistema para que usuarios confirmen o reporten errores en datos extraídos, con estados de verificación progresivos
- `api-rest`: FastAPI con endpoints REST documentados (OpenAPI), Docker Compose para infraestructura

### Modified Capabilities
<!-- Ninguna, es un proyecto nuevo -->

## Impact

- **Nuevo backend** en Python/FastAPI + SQLAlchemy + PostgreSQL
- **Nueva dependencia externa**: API de Gemini (google-generativeai)
- **Nuevo pipeline de procesamiento**: subida imagen → VLM → validación → DB
- **Almacenamiento**: Imágenes originales guardadas en disco local o S3 configurable
- **Infraestructura**: Docker Compose para PostgreSQL, Dockerfile para la app
- **No afecta** sistemas existentes (proyecto desde cero)
