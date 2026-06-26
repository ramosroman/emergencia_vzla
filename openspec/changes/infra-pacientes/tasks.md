## 1. Setup del proyecto

- [x] 1.1 Crear estructura de directorios `backend/` con subcarpetas `app/models`, `app/schemas`, `app/routers`, `app/services`, `app/utils`
- [x] 1.2 Crear `requirements.txt` con dependencias: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic, pydantic-settings, python-multipart, google-generativeai, Pillow, python-dotenv
- [x] 1.3 Crear `Dockerfile` para la app FastAPI (Python 3.12 slim, instalar requirements, exponer puerto 8000)
- [x] 1.4 Crear `docker-compose.yml` con servicios: `app` (build local, puerto 8000, volumen uploads) y `db` (postgres:16, volumen pgdata, puerto 5432)
- [x] 1.5 Crear `.env.example` con variables: `GEMINI_API_KEY`, `DATABASE_URL`, `UPLOAD_DIR`, `CORS_ORIGINS`
- [x] 1.6 Verificar que `docker compose up --build` inicia correctamente ambos servicios

## 2. Configuración y base de datos

- [x] 2.1 Crear `app/config.py` usando `pydantic-settings` para leer variables de entorno
- [x] 2.2 Crear `app/database.py` con engine SQLAlchemy async + async session factory
- [x] 2.3 Crear `app/models/paciente.py`: modelo SQLAlchemy para tabla `pacientes` (todos los campos del diseño)
- [x] 2.4 Crear `app/models/extraccion.py`: modelo SQLAlchemy para tabla `extracciones` con JSONB raw_output
- [x] 2.5 Crear `app/models/verificacion.py`: modelo SQLAlchemy para tabla `verificaciones` con unique constraint (paciente_id, verificador_id)
- [x] 2.6 Crear script de inicialización de tablas (create_all / Alembic básico)
- [ ] 2.7 Verificar que las tablas se crean correctamente al iniciar la app

## 3. Modelos Pydantic (schemas)

- [x] 3.1 Crear `app/schemas/paciente.py`: PacienteCreate, PacienteRead, PacienteList (con paginación)
- [x] 3.2 Crear `app/schemas/extraccion.py`: ExtraccionRead, ExtraccionResult (respuesta post-extracción con completos/parciales)
- [x] 3.3 Crear `app/schemas/busqueda.py`: BusquedaParams, BusquedaResult, BusquedaError
- [x] 3.4 Crear `app/schemas/verificacion.py`: VerificacionCreate, VerificacionRead, VerificacionStats
- [x] 3.5 Crear `app/schemas/respuesta.py`: esquemas genéricos de respuesta (ErrorResponse, SuccessResponse)

## 4. Servicio Gemini (VLM)

- [x] 4.1 Crear `app/services/gemini_service.py` con función `extraer_datos_desde_imagen(ruta_imagen) -> dict`
- [x] 4.2 Integrar el prompt refinado (versión con pacientes_completos/pacientes_parciales) como constante
- [x] 4.3 Configurar llamada a Gemini 2.0 Flash con `temperature=0.1`, `max_output_tokens=4096`
- [x] 4.4 Implementar parseo de la respuesta JSON de Gemini con validación Pydantic
- [x] 4.5 Manejar errores: timeout, respuesta no-JSON, API key inválida, cuota excedida (429)
- [ ] 4.6 Verificar con una imagen de prueba que el servicio devuelve datos estructurados

## 5. Servicio de extracción (orquestación)

- [x] 5.1 Crear `app/services/extraccion_service.py` con función `procesar_imagen(ruta_imagen) -> ExtraccionResult`
- [x] 5.2 Implementar flujo: validar imagen → guardar → llamar Gemini → parsear → separar completos/parciales
- [x] 5.3 Implementar lógica de duplicados: si ya existe paciente con misma cédula, vincular nueva extracción
- [x] 5.4 Guardar pacientes_completos en DB con sus extracciones
- [x] 5.5 Registrar pacientes_parciales en log (no crear pacientes)
- [x] 5.6 Devolver respuesta con pacientes creados, totales y advertencias
- [x] 5.7 Crear `app/utils/imagen.py` para validación (formato, tamaño) y preprocesamiento básico

## 6. CRUD de pacientes

- [x] 6.1 Crear `app/services/pacientes_service.py` con funciones: `listar_pacientes()`, `obtener_paciente()`, `obtener_extracciones()`
- [x] 6.2 Implementar paginación (limit/offset) en listar pacientes
- [x] 6.3 Implementar búsqueda por cédula (exacta, normalizada)
- [x] 6.4 Implementar búsqueda por nombre (ILIKE, unicode normalization)
- [x] 6.5 Implementar búsqueda global (q) que busca en cédula y nombre
- [x] 6.6 Implementar servicio para servir imagen original del paciente

## 7. Verificación comunitaria

- [x] 7.1 Crear `app/services/verificacion_service.py` con función `registrar_voto(paciente_id, verificador_id, tipo, comentario)`
- [x] 7.2 Implementar lógica de unique constraint (1 voto por persona por paciente)
- [x] 7.3 Implementar actualización automática de `status_verificacion` según reglas
- [x] 7.4 Implementar conteo de votos (confirmaciones y reportes) para incluir en respuestas

## 8. Routers (endpoints REST)

- [x] 8.1 Crear `app/routers/pacientes.py`: GET /api/v1/pacientes, GET /api/v1/pacientes/{id}, GET /api/v1/pacientes/{id}/imagen, GET /api/v1/pacientes/{id}/extracciones
- [x] 8.2 Crear `app/routers/extraccion.py`: POST /api/v1/extraccion/upload (aceptar archivo, llamar servicio, devolver resultado)
- [x] 8.3 Crear `app/routers/busqueda.py`: GET /api/v1/busqueda?cedula=X, GET /api/v1/busqueda?nombre=X, GET /api/v1/busqueda?q=X
- [x] 8.4 Crear `app/routers/verificaciones.py`: POST /api/v1/verificaciones/{paciente_id}, GET /api/v1/verificaciones/{paciente_id}
- [x] 8.5 Crear `app/main.py`: instanciar FastAPI, incluir routers, configurar CORS, lifespan con init_db

## 9. Integración y pruebas

- [ ] 9.1 Verificar Docker Compose completo (app + db funcionando juntos)
      → Requiere ejecutar `docker compose up --build` en backend/
- [ ] 9.2 Probar subida de imagen real
      → Requiere GEMINI_API_KEY configurada y app corriendo
- [ ] 9.3 Probar búsqueda por cédula y nombre
      → Depende de 9.2 (datos en DB)
- [ ] 9.4 Probar ciclo de verificación: confirmar → cambiar estado
      → Depende de 9.2
- [ ] 9.5 Probar manejo de errores: 404, 409, 413, 415, 422
      → Depende de app corriendo
- [ ] 9.6 Verificar documentación OpenAPI en /docs
      → Depende de app corriendo
