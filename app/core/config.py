import re
from functools import lru_cache
from urllib.parse import quote

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

_ESQUEMA_LIBPQ = "postgresql://"
_PG_ASYNC_DRIVER = "postgresql+asyncpg"

# Coolify/Dokku/Heroku a veces mandan postgres:// o Postgres+Raro://; el entrypoint
# registrado en SQLAlchemy es "postgresql", no "postgres" → NoSuchModuleError si no normalizamos.
_PG_SCHEME_FIX = re.compile(r"^postgres(\+[a-z0-9]+)?://", re.IGNORECASE)


def _normalizar_esquema_postgres(url: str) -> str:
    """Fuerza esquema libpq/SQLAlchemy válido (postgresql) antes de make_url/create_engine."""
    s = (url or "").strip().lstrip("\ufeff\ufffe")
    # Coolify/UI a veces guardan BOM u otro prefijo invisible; sin esto el regex ^postgres no engancha
    s = _PG_SCHEME_FIX.sub(lambda m: f"postgresql{m.group(1) or ''}://", s)
    return s


def normalizar_para_async_pg_engine(url: str) -> str:
    """Siempre postgresql+asyncpg tras saneado de esquema (cualquier driver legacy o dummy postgres)."""
    s = (url or "").strip().lstrip("\ufeff\ufffe")
    if not s:
        raise ValueError("URL de base de datos vacía para el motor async")
    saneada = _normalizar_esquema_postgres(s)
    u = make_url(saneada)
    # Una sola fuente de verdad de driver: evita ramas donde make_url aún deja dialecto «postgres»
    u = u.set(drivername=_PG_ASYNC_DRIVER)
    return u.render_as_string(hide_password=False)


class Settings(BaseSettings):
    """Config desde env: .env base y .env.local (este último gana; no subir a git)."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        # Coolify y otros orquestadores suelen inyectar database_url en minúsculas
        case_sensitive=False,
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
            "database_url",
            "POSTGRES_URL",
            "postgres_url",
            # URL completa donde el esquema suele ir como postgres:// (no postgresql); lo normaliza el código.
            "DATABASE_URI",
            "database_uri",
            "POSTGRES_DATABASE_URL",
            "SQLALCHEMY_DATABASE_URI",
            "sqlalchemy_database_uri",
            # Plantilla interna de algunos PaaS
            "COOLIFY_DATABASE_URL",
            "coolify_database_url",
        ),
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalizar_esquema_url_coolify(cls, valor: object) -> str | None:
        """postgres:// en el momento del parseo: evita dialecto legacy antes de make_url en session."""
        if valor is None:
            return None
        if not isinstance(valor, str):
            return None
        s = valor.strip().lstrip("\ufeff\ufffe")
        if not s:
            return None
        return _normalizar_esquema_postgres(s)

    GITHUB_USERNAME: str = "Abelserradev"
    GITHUB_TOKEN: str | None = None
    REDIS_URL: str | None = None
    GITHUB_CACHE_TTL_SECONDS: int = 900
    GITHUB_CACHE_STALE_SECONDS: int = 43_200

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
        url_completa = (self.DATABASE_URL or "").strip()
        if url_completa:
            # DATABASE_URL es la fuente de verdad en Coolify; POSTGRES_* queda como fallback local.
            return _normalizar_esquema_postgres(url_completa)
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
        if (self.DATABASE_URL or "").strip() or self.POSTGRES_SERVER:
            return self
        raise ValueError(
            "Define DATABASE_URL o POSTGRES_SERVER para conectar a PostgreSQL."
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
