from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    debug: bool = False
    database_url: str = "postgresql+asyncpg://meridian:meridian@localhost:5432/meridian"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]

    anthropic_api_key: str = ""

    workos_api_key: str = ""
    workos_client_id: str = ""
    workos_cookie_password: str = ""
    workos_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"


settings = Settings()
