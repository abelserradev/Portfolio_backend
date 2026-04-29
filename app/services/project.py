from typing import Optional
from app.repositories.base import AbstractRepository
from app.models.project import Project

class ProjectService:
    def __init__(self, repository: AbstractRepository[Project]):
        self.repo = repository

    async def get_project(self, id: int) -> Optional[Project]:
        return await self.repo.get(id)

    async def get_projects(self, skip: int = 0, limit: int = 100) -> list[Project]:
        return await self.repo.list(skip, limit)

    async def create_project(self, project_data: dict) -> Project:
        project = Project(**project_data)
        return await self.repo.add(project)

    async def update_project(self, id: int, project_data: dict) -> Optional[Project]:
        project = await self.repo.get(id)
        if not project:
            return None
        for key, value in project_data.items():
            setattr(project, key, value)
        return await self.repo.update(project)

    async def delete_project(self, id: int) -> bool:
        project = await self.repo.get(id)
        if not project:
            return False
        await self.repo.delete(id)
        return True

    async def increment_visits(self, id: int) -> Optional[Project]:
        project = await self.repo.get(id)
        if not project:
            return None
        project.visits = (project.visits or 0) + 1
        return await self.repo.update(project)