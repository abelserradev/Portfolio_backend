from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.core.config import get_settings
from app.schemas.github import LanguageStat
from app.security.rate_limit import construir_limiter
from app.services.github import GithubService

router = APIRouter()
_settings = get_settings()
_lim = construir_limiter(_settings.RATE_LIMIT_DEFAULT)


def get_github_service() -> GithubService:
    return GithubService()


@router.get("/languages", response_model=list[LanguageStat])
@_lim.limit(_settings.RATE_LIMIT_GITHUB)
async def get_github_languages(
    request: Request,
    response: Response,
    github_service: Annotated[GithubService, Depends(get_github_service)],
):
    """
    Obtiene los lenguajes más utilizados en los repositorios de GitHub del usuario,
    calculando el porcentaje basado en los bytes de código.
    """
    return await github_service.get_user_languages()
