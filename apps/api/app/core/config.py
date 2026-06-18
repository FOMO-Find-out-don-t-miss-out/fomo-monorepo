import json

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
    # Stored as a plain str so pydantic-settings never attempts JSON pre-parsing.
    # Use cors_allowed_origins_list to get the parsed list for CORSMiddleware.
    # Accepts comma-separated (preferred for Kubernetes ConfigMaps) or a JSON array.
    # Example: CORS_ALLOWED_ORIGINS=https://dashboard.staging.fomo-lab.org,http://localhost:3000
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        raw = self.CORS_ALLOWED_ORIGINS.strip()
        if not raw:
            return []
        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError(
                    f"CORS_ALLOWED_ORIGINS JSON must be an array, got {type(parsed).__name__}"
                )
            return [str(v).strip() for v in parsed if str(v).strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

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

    # OIDC / Keycloak JWT authentication.
    # Set AUTH_OIDC_ENABLED=true in staging/prod to enforce JWT validation.
    # When false (default), get_current_identity returns None and
    # require_authenticated_identity raises HTTP 503 (misconfiguration signal).
    AUTH_OIDC_ENABLED: bool = False
    # Primary OIDC issuer (e.g. fomo-admin realm for dashboard users).
    # The JWKS URL is derived automatically as {issuer}/protocol/openid-connect/certs
    # unless AUTH_OIDC_JWKS_URL is explicitly set.
    AUTH_OIDC_ISSUER: str | None = None
    AUTH_OIDC_JWKS_URL: str | None = None
    AUTH_OIDC_CLIENT_ID: str | None = None
    # Comma-separated additional issuers beyond AUTH_OIDC_ISSUER.
    # Each issuer's JWKS URL is derived automatically via Keycloak convention.
    # Example: AUTH_OIDC_EXTRA_ISSUERS=https://auth.fomo-lab.org/realms/fomo-users
    AUTH_OIDC_EXTRA_ISSUERS: str = ""
    # Comma-separated allowed aud values.  Empty = audience claim not validated.
    # Keycloak public clients often omit client_id from aud; prefer azp validation.
    AUTH_OIDC_ALLOWED_AUDIENCES: str = ""
    # Comma-separated allowed azp values.  Empty = azp claim not validated.
    # azp is the Keycloak client that requested the token — reliable for public clients.
    AUTH_OIDC_ALLOWED_AZP: str = ""

    @property
    def oidc_allowed_issuers_list(self) -> list[str]:
        """All trusted OIDC issuers: primary + any extras."""
        issuers: list[str] = []
        if self.AUTH_OIDC_ISSUER:
            issuers.append(self.AUTH_OIDC_ISSUER)
        for v in self.AUTH_OIDC_EXTRA_ISSUERS.split(","):
            v = v.strip()
            if v and v not in issuers:
                issuers.append(v)
        return issuers

    @property
    def oidc_allowed_audiences_list(self) -> list[str]:
        return [v.strip() for v in self.AUTH_OIDC_ALLOWED_AUDIENCES.split(",") if v.strip()]

    @property
    def oidc_allowed_azp_list(self) -> list[str]:
        return [v.strip() for v in self.AUTH_OIDC_ALLOWED_AZP.split(",") if v.strip()]

    # Keycloak Admin REST API — used by backend-only admin flows (e.g. user invite).
    # Must be a service account with "manage-users" realm role in the target realm.
    # Set all four vars; any missing var disables admin features gracefully.
    # Platform follow-up: inject these via fomo-platform secrets/ConfigMap.
    KEYCLOAK_ADMIN_BASE_URL: str | None = None  # e.g. https://auth.fomo-lab.org
    KEYCLOAK_ADMIN_REALM: str = "fomo-admin"
    KEYCLOAK_ADMIN_CLIENT_ID: str | None = None   # service-account client id
    KEYCLOAK_ADMIN_CLIENT_SECRET: str | None = None  # service-account client secret

    @property
    def keycloak_admin_configured(self) -> bool:
        return bool(
            self.KEYCLOAK_ADMIN_BASE_URL
            and self.KEYCLOAK_ADMIN_CLIENT_ID
            and self.KEYCLOAK_ADMIN_CLIENT_SECRET
        )

    # OpenTelemetry tracing — disabled by default; platform sets these in staging/prod.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "fomo-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = 0.1


settings = Settings()
