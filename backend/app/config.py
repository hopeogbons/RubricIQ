from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    env: str = "development"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    superadmin_email: str | None = None
    superadmin_password: str | None = None

    resend_api_key: str | None = None
    resend_from_email: str = "RubricIQ <noreply@rubriciq.com>"
    frontend_base_url: str = "http://localhost:5173"


settings = Settings()
