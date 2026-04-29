from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import projects, github
from app.core.config import get_settings
from app.db.init_db import inicializar_base_y_datos

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

# CORS para tu frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(github.router, prefix=f"{settings.API_V1_STR}/github")
# app.include_router(contact.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Bienvenido a la API del portfolio"}
    