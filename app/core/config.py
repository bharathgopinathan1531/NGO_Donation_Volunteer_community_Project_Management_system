from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "NGO Management System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./ngo_dev.db"

    SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    EXPOSE_RESET_TOKEN: bool = False

    SUPER_ADMIN_EMAIL: str = "admin@ngo.org"
    SUPER_ADMIN_PASSWORD: str = "Admin@12345"
    SUPER_ADMIN_NAME: str = "Super Admin"

    DEADLINE_ALERT_DAYS: int = 7
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def validate_for_production(self) -> None:
        """Refuse to boot in production with insecure configuration."""
        if not self.is_production:
            return
        if self.SECRET_KEY in {"change-me", ""} or len(self.SECRET_KEY) < 32:
            raise RuntimeError("SECRET_KEY must be a random string of at least 32 characters in production")
        if self.EXPOSE_RESET_TOKEN:
            raise RuntimeError("EXPOSE_RESET_TOKEN must be false in production")
        if self.DEBUG:
            raise RuntimeError("DEBUG must be false in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
