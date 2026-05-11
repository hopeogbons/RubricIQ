from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    env: str = "development"

    # CORS allow-list. Defaults to the Vite/CRA dev ports; production should
    # set CORS_ALLOW_ORIGINS to the public app origin (comma-separated for
    # multiple). Wildcards are not supported; SPEC requires explicit origins.
    cors_allow_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return value

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    superadmin_email: str | None = None
    superadmin_password: str | None = None

    resend_api_key: str | None = None
    resend_from_email: str = "RubricIQ <noreply@rubriciq.com>"
    frontend_base_url: str = "http://localhost:5173"

    artifact_dir: str = "/data/artifacts"
    artifact_signing_secret: str
    max_file_bytes: int = 100 * 1024 * 1024
    max_submission_bytes: int = 500 * 1024 * 1024

    n8n_webhook_url: str | None = None
    n8n_webhook_secret: str | None = None
    callback_secret: str
    public_api_base_url: str = "http://localhost:8000"

    cleanup_enabled: bool = True
    cleanup_interval_minutes: int = 60
    artifact_ttl_hours: int = 6
    stuck_after_minutes: int = 30


settings = Settings()
