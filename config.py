from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    ADMIN_ID: int | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()