from fastapi import APIRouter, Depends
from app.services.github import GithubService
from app.schemas.github import LanguageStat

router = APIRouter()

def get_github_service() -> GithubService:
    return GithubService()

@router.get("/languages", response_model=list[LanguageStat])
async def get_github_languages(github_service: GithubService = Depends(get_github_service)):
    """
    Obtiene los lenguajes más utilizados en los repositorios de GitHub del usuario,
    calculando el porcentaje basado en los bytes de código.
    """
    return await github_service.get_user_languages()
