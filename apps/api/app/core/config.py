from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/fomo"
    REDIS_URL: str = "redis://redis:6379/0"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FOMO API"
    N8N_WEBHOOK_URL: str | None = None
    GOOGLE_API_KEY: str | None = None
    MAPBOX_ACCESS_TOKEN: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    SCRAPER_PROXY_URL: str | None = None

    # OpenTelemetry tracing — disabled by default; platform sets these in staging/prod.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "fomo-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = 0.1


settings = Settings()
