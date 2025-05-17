from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    xyte_api_key: str = Field(..., alias="XYTE_API_KEY")
    xyte_base_url: str = Field(
        "https://hub.xyte.io/core/v1/organization", alias="XYTE_BASE_URL"
    )
    xyte_user_token: str | None = Field(default=None, alias="XYTE_USER_TOKEN")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
