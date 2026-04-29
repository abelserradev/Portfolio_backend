from functools import lru_cache
from urllib.parse import quote

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

_ESQUEMA_LIBPQ = "postgresql://"
_PG_URL_CORTO = "postgres://"

def _normalizar_esquema_postgres(url: str) -> str:
    """Coolify/Heroku suelen usar postgres:// ; SQLAlchemy sólo reconoce postgresql://."""
    s = url.strip()
    low = s.lower()
    # postgresql:// se deja tal cual; postgres:// (cualquier capitalización) se normaliza.
    if low.startswith(_PG_URL_CORTO) and not low.startswith(_ESQUEMA_LIBPQ):
        return _ESQUEMA_LIBPQ + s[len(_PG_URL_CORTO) :]
    return s


def normalizar_para_async_pg_engine(url: str) -> str:
    """Evita sqlalchemy.dialects:postgres cuando Coolify manda postgres://."""
    saneada = _normalizar_esquema_postgres(url.strip())
    u = make_url(saneada)
    if u.drivername == "postgres":
        u = u.set(drivername="postgresql")
    if u.drivername == "postgresql":
        return str(u.set(drivername="postgresql+asyncpg"))
    if u.drivername == "postgresql+asyncpg":
        return str(u)
    return str(u)


class Settings(BaseSettings):
    """Config desde env (.env local y variables de Coolify)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Portfolio Api"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str | None = Field(
        default=None,
        validation_alias=AliasChoices("POSTGRES_SERVER", "PGHOST"),
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        validation_alias=AliasChoices("POSTGRES_PORT", "PGPORT"),
    )
    POSTGRES_USER: str = Field(
        default="postgres",
        validation_alias=AliasChoices("POSTGRES_USER", "PGUSER"),
    )
    POSTGRES_PASSWORD: str = Field(
        default="postgres",
        validation_alias=AliasChoices("POSTGRES_PASSWORD", "PGPASSWORD"),
    )
    # Nombre BD (Coolify suele llamar igual el servicio y la cuenta; también PGDATABASE típico de libpq)
    POSTGRES_DB: str = Field(
        default="postgres",
        validation_alias=AliasChoices("POSTGRES_DB", "PGDATABASE"),
    )
    DATABASE_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "POSTGRES_URL",
            # URL completa donde el esquema suele ir como postgres:// (no postgresql); lo normaliza el código.
            "DATABASE_URI",
            "POSTGRES_DATABASE_URL",
        ),
    )

    GITHUB_USERNAME: str = "Abelserradev"
    GITHUB_TOKEN: str | None = None

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Seguridad HTTP (ver main.py)
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_GITHUB: str = "30/minute"
    # Lista separada por comas. Vacío = no aplicar TrustedHostMiddleware (útil en dev).
    TRUSTED_HOSTS: str = ""
    # >0 envía HSTS (solo si el servicio ya se sirve por HTTPS delante del cliente)
    SECURITY_HSTS_SECONDS: int = 0

    @property
    def trusted_hosts_list(self) -> list[str]:
        raw = (self.TRUSTED_HOSTS or "").strip()
        if not raw:
            return []
        return [h.strip() for h in raw.split(",") if h.strip()]

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            # DATABASE_URL es la fuente de verdad en Coolify; POSTGRES_* queda como fallback local.
            return _normalizar_esquema_postgres(self.DATABASE_URL)
        if not self.POSTGRES_SERVER:
            raise ValueError(
                "Sin DATABASE_URL debes definir POSTGRES_SERVER (y credenciales coherentes)."
            )
        user = quote(self.POSTGRES_USER, safe="")
        password = quote(self.POSTGRES_PASSWORD, safe="")
        return f"{_ESQUEMA_LIBPQ}{user}:{password}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        return normalizar_para_async_pg_engine(self.sync_database_url)

    @model_validator(mode="after")
    def validar_alternativa_conexion(self) -> "Settings":
        if self.DATABASE_URL or self.POSTGRES_SERVER:
            return self
        raise ValueError(
            "Define DATABASE_URL o POSTGRES_SERVER para conectar a PostgreSQL."
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
