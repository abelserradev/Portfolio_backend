from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Portfolio Api"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "portfolio"
    DATABASE_URL: str | None = None

    GITHUB_USERNAME: str = "Abelserradev"
    GITHUB_TOKEN: str | None = None

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL or f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"
    
    @property
    def async_database_url(self) -> str:
        base = self.sync_database_url.replace("postgresql://", "postgresql+asyncpg://")
        return base

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
    