from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Telegram
    telegram_api_id: int = 35507477
    telegram_api_hash: str = "201ab47b2a808cc66c3ef61529dba649"
    telegram_phone: str = "+998775013234"
    telegram_session_string: str = ""

    # ELD
    eld_base_url: str = "https://api.drivehos.app/api/v1"
    eld_bearer_token: str = ""
    eld_tenant_id: str = "96335ac3-5a93-4a29-af8b-08d874801325"

    # App
    poll_interval_seconds: int = 300
    app_secret_key: str = "eld-monitor-secret"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
