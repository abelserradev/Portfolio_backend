import os
from functools import lru_cache
from urllib.parse import quote, urlparse, urlunparse

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ESQUEMA_LIBPQ = "postgresql://"
_PG_URL_CORTO = "postgres://"
_PG_ASYNC = "postgresql+asyncpg://"


def _normalizar_esquema_postgres(url: str) -> str:
    """Coolify/Heroku suelen usar postgres:// ; SQLAlchemy sólo reconoce postgresql://."""
    s = url.strip()
    low = s.lower()
    # postgresql:// se deja tal cual; postgres:// (cualquier capitalización) se normaliza.
    if low.startswith(_PG_URL_CORTO) and not low.startswith(_ESQUEMA_LIBPQ):
        return _ESQUEMA_LIBPQ + s[len(_PG_URL_CORTO) :]
    return s


def _sustituir_nombre_bd_en_url(url: str, nuevo_nombre: str) -> str:
    """Solo el path tras el host (/dbname)."""
    parsed = urlparse(url)
    path = nuevo_nombre.strip().strip("/")
    return urlunparse(parsed._replace(path=f"/{path}"))


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

    POSTGRES_SERVER: str | None = None
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    # Nombre BD: env POSTGRES_DB o PGDATABASE (CLI/libpq)
    POSTGRES_DB: str = Field(
        default="postgres",
        validation_alias=AliasChoices("POSTGRES_DB", "PGDATABASE"),
    )

    DATABASE_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL"),
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
            url = _normalizar_esquema_postgres(self.DATABASE_URL)
            # Sustituir nombre de BD de la URL solo si viene en variables de proceso (Coolify/OS).
            # POSTGRES_* en .env llega al modelo pero suele NO estar en os.environ; así conservamos el
            # sufijo .../dbname de DATABASE_URL cuando la URL viene completa desde despliegue.
            env_definio_bd_proc = ("POSTGRES_DB" in os.environ) or ("PGDATABASE" in os.environ)
            if env_definio_bd_proc:
                url = _sustituir_nombre_bd_en_url(url, self.POSTGRES_DB)
            return url
        if not self.POSTGRES_SERVER:
            raise ValueError(
                "Sin DATABASE_URL debes definir POSTGRES_SERVER (y credenciales coherentes)."
            )
        user = quote(self.POSTGRES_USER, safe="")
        password = quote(self.POSTGRES_PASSWORD, safe="")
        return f"{_ESQUEMA_LIBPQ}{user}:{password}@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        # Doble pasada por si algún día sync_url devolviera postgres:// sin normalizar por completo.
        sync = _normalizar_esquema_postgres(self.sync_database_url)
        return sync.replace(_ESQUEMA_LIBPQ, _PG_ASYNC, 1)

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
