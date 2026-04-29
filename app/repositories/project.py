from app.models.project import Project
from app.repositories.base import SqlAlchemyRepository

class ProjectRepository(SqlAlchemyRepository[Project]):
    def __init__(self, session):
        super().__init__(session, Project)