from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.repositories.project import ProjectRepository
from app.services.cache import RedisCache
from app.services.chat_service import ChatService
from app.services.github import GithubService
from app.services.lead_notifier import LeadNotifier
from app.services.ollama_client import OllamaClient
from app.services.project import ProjectService


@lru_cache
def _redis_cache_singleton() -> RedisCache:
    return RedisCache()


def get_redis_cache() -> RedisCache:
    return _redis_cache_singleton()


def get_ollama_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> OllamaClient:
    return OllamaClient(settings)


def get_lead_notifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LeadNotifier:
    return LeadNotifier(settings)


def get_project_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ProjectService:
    repository = ProjectRepository(db)
    return ProjectService(repository)


def get_github_service(
    cache: Annotated[RedisCache, Depends(get_redis_cache)],
) -> GithubService:
    return GithubService(cache=cache)


def get_chat_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    ollama: Annotated[OllamaClient, Depends(get_ollama_client)],
    notifier: Annotated[LeadNotifier, Depends(get_lead_notifier)],
) -> ChatService:
    return ChatService(
        settings=settings,
        db=db,
        ollama=ollama,
        notifier=notifier,
    )
