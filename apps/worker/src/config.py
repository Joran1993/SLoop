from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_role_key: str

    sentry_dsn: str = ""

    koop_poll_interval_hours: int = 6
    koop_lookback_days: int = 2
    pipeline_lookback_days: int = 90

    resend_api_key: str = ""
    resend_from_email: str = "Sloopradar <alerts@sloopradar.nl>"


settings = Settings()
