from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    cors_origins: list[str] = ["http://localhost:3000"]
    app_base_url: str = "http://localhost:8000"
    debug: bool = True

    sentry_dsn: str = ""

    mollie_api_key: str = ""
    mollie_webhook_secret: str = ""

    resend_api_key: str = ""


settings = Settings()
