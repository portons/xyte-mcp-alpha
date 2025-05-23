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
    environment: str = Field(default="prod", alias="XYTE_ENV")
    rate_limit_per_minute: int = Field(default=60, alias="XYTE_RATE_LIMIT")
    mcp_inspector_port: int = Field(default=8080, alias="MCP_INSPECTOR_PORT")
    mcp_inspector_host: str = Field(default="127.0.0.1", alias="MCP_INSPECTOR_HOST")
    enable_experimental_apis: bool = Field(
        default=False, alias="XYTE_EXPERIMENTAL_APIS"
    )
    xyte_api_mapping: str | None = Field(default=None, alias="XYTE_API_MAPPING")
    xyte_hooks_module: str | None = Field(default=None, alias="XYTE_HOOKS_MODULE")
    log_level: str = Field(default="INFO", alias="XYTE_LOG_LEVEL")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    settings = Settings()
    validate_settings(settings)
    return settings


def reload_settings() -> None:
    """Clear cached settings so they will be reloaded on next access."""
    get_settings.cache_clear()


def validate_settings(settings: Settings) -> None:
    """Validate critical configuration values and raise ``ValueError`` if invalid."""
    if not (settings.xyte_api_key or settings.xyte_oauth_token or settings.xyte_user_token):
        raise ValueError("XYTE_API_KEY, XYTE_OAUTH_TOKEN, or XYTE_USER_TOKEN must be set")
    if settings.rate_limit_per_minute <= 0:
        raise ValueError("XYTE_RATE_LIMIT must be positive")
    if settings.xyte_cache_ttl <= 0:
        raise ValueError("XYTE_CACHE_TTL must be positive")
    if not settings.xyte_base_url:
        raise ValueError("XYTE_BASE_URL must not be empty")
