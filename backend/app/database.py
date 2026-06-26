import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db(max_retries: int = 10, retry_delay: float = 2.0) -> None:
    """
    Crear todas las tablas si no existen, con reintentos para esperar
    a que PostgreSQL esté listo (útil en Docker Compose).

    Args:
        max_retries: Número máximo de reintentos.
        retry_delay: Segundos entre reintentos.
    """
    # Importar modelos aquí para registrar metadata en Base y evitar
    # importación circular (models → database → models)
    import app.models.paciente  # noqa: F401
    import app.models.extraccion  # noqa: F401
    import app.models.verificacion  # noqa: F401

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Tablas creadas/verificadas correctamente (intento %d/%d)", attempt, max_retries)
            return
        except OperationalError as exc:
            last_error = exc
            logger.warning(
                "Base de datos no disponible (intento %d/%d): %s",
                attempt, max_retries, exc,
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)

    logger.error("No se pudo conectar a la BD después de %d intentos", max_retries)
    raise last_error or RuntimeError("No se pudo inicializar la base de datos")


async def get_db() -> AsyncSession:
    """Dependency para obtener una sesión de base de datos."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
