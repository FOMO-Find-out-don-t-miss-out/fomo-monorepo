import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/fomo"
    REDIS_URL: str = "redis://redis:6379/0"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FOMO API"
    N8N_WEBHOOK_URL: str | None = None
    MAPBOX_ACCESS_TOKEN: str | None = None
    SCRAPER_PROXY_URL: str | None = None

    # CORS — origins the browser is allowed to call the API from.
    # Accepts a JSON array or a comma-separated string.
    # Example: CORS_ALLOWED_ORIGINS=["https://dashboard.staging.fomo-lab.org","http://localhost:3000"]
    CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        raise ValueError(f"CORS_ALLOWED_ORIGINS must be a list or string, got {type(v)}")

    # AI provider configuration
    AI_EXTRACTION_ENABLED: bool = False
    AI_PROVIDER: str = "disabled"  # "disabled" | "deepseek" | "gemini"
    AI_MODEL: str = "deepseek-chat"
    AI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None  # alias; used if AI_API_KEY is not set
    AI_BASE_URL: str = "https://api.deepseek.com"
    AI_MAX_INPUT_CHARS: int = 12000
    AI_MAX_OUTPUT_TOKENS: int = 800
    AI_REQUEST_TIMEOUT_SECONDS: int = 20

    # Legacy Gemini settings — used only when AI_PROVIDER=gemini
    GOOGLE_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # OpenTelemetry tracing — disabled by default; platform sets these in staging/prod.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "fomo-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = 0.1


settings = Settings()
