from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.endpoints import github, projects
from app.core.config import get_settings
from app.db.init_db import inicializar_base_y_datos
from app.security.middleware_security import MiddlewareCabecerasSeguridad
from app.security.rate_limit import construir_limiter

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Crea tablas en el arranque y siembra el primer proyecto público cuando aplica."""
    await inicializar_base_y_datos()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

limiter = construir_limiter(settings.RATE_LIMIT_DEFAULT)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Starlette ejecuta antes la última capa registrada: CORS al final garantiza cabeceras
# en errores generados dentro de la pila interna (p. ej. rate limit).
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    MiddlewareCabecerasSeguridad,
    segundo_hsts=settings.SECURITY_HSTS_SECONDS,
)
trusted = settings.trusted_hosts_list
if trusted:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted,
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(github.router, prefix=f"{settings.API_V1_STR}/github")


@app.get("/")
async def root():
    return {"message": "Bienvenido a la API del portfolio"}
