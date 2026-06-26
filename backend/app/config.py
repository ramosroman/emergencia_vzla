from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "postgresql+asyncpg://app:app_secret_123@localhost:5432/pacientes"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 8192

    # Archivos
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 20

    # CORS
    cors_origins: str = "*"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
