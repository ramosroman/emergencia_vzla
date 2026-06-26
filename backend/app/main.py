import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    logger.info("Iniciando aplicación...")

    # Inicializar base de datos (crear tablas si no existen)
    await init_db()
    logger.info("Base de datos inicializada correctamente")

    yield

    logger.info("Apagando aplicación...")


# Crear la aplicación FastAPI
app = FastAPI(
    title="Emergencia Venezuela - Pacientes API",
    description=(
        "API para centralizar listados hospitalarios durante emergencias. "
        "Permite subir imágenes de listados, extraer datos con VLM (Gemini), "
        "buscar pacientes y verificar información comunitariamente."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
from app.routers import busqueda, extraccion, pacientes, verificaciones

app.include_router(pacientes.router)
app.include_router(extraccion.router)
app.include_router(busqueda.router)
app.include_router(verificaciones.router)


@app.get("/")
async def root():
    return {
        "app": "Emergencia Venezuela - Pacientes API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
