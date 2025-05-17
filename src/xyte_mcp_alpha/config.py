from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    xyte_api_key: str | None = Field(default=None, alias="XYTE_API_KEY")
    xyte_oauth_token: str | None = Field(default=None, alias="XYTE_OAUTH_TOKEN")
    xyte_base_url: str = Field(
        default="https://hub.xyte.io/core/v1/organization", alias="XYTE_BASE_URL"
    )
    xyte_user_token: str | None = Field(default=None, alias="XYTE_USER_TOKEN")
    xyte_cache_ttl: int = Field(default=60, alias="XYTE_CACHE_TTL")
    environment: str = Field("prod", alias="XYTE_ENV")
    rate_limit_per_minute: int = Field(default=60, alias="XYTE_RATE_LIMIT")
    mcp_inspector_port: int = Field(default=8080, alias="MCP_INSPECTOR_PORT")
<<<<<<< HEAD
    enable_experimental_apis: bool = Field(
        default=False, alias="XYTE_EXPERIMENTAL_APIS"
    )
=======
    xyte_api_mapping: str | None = Field(default=None, alias="XYTE_API_MAPPING")
    xyte_hooks_module: str | None = Field(default=None, alias="XYTE_HOOKS_MODULE")
>>>>>>> 027fe7871d9911d28c1c81ba6df3bed5fa10b5cd


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def reload_settings() -> None:
    """Clear cached settings so they will be reloaded on next access."""
    get_settings.cache_clear()
