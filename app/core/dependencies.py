from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.project import ProjectRepository
from app.services.project import ProjectService
from app.services.chat_service import ChatService
from app.services.lead_notifier import LeadNotifier
from app.services.ollama_client import OllamaClient

def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    repository = ProjectRepository(db)
    return ProjectService(repository)


def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    settings = get_settings()
    return ChatService(
        settings=settings,
        db=db,
        ollama=OllamaClient(settings),
        notifier=LeadNotifier(settings),
    )
