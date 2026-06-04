from sqlalchemy import desc, select

from app.models.project import Project
from app.repositories.base import SqlAlchemyRepository


class ProjectRepository(SqlAlchemyRepository[Project]):
    def __init__(self, session):
        super().__init__(session, Project)

    async def list(self, skip: int = 0, limit: int = 100) -> list[Project]:
        # Destacados y sort_order primero: el visitante ve el MVP activo arriba del grid
        stmt = (
            select(Project)
            .order_by(desc(Project.is_featured), Project.sort_order, Project.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())