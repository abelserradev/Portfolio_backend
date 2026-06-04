from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.db.base import Base
from app.models.project_status import ProjectStatus


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    tech_stack = Column(String(300))
    live_url = Column(String(500))
    repo_url = Column(String(500))
    image_url = Column(String(500))
    status = Column(
        String(32),
        nullable=False,
        default=ProjectStatus.LIVE.value,
        server_default=ProjectStatus.LIVE.value,
    )
    is_featured = Column(Boolean, nullable=False, default=False, server_default="false")
    sort_order = Column(Integer, nullable=False, default=100, server_default="100")
    visits = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())