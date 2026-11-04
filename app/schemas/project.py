from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.project_status import ProjectStatusLiteral


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=20000)
    tech_stack: Optional[str] = Field(None, max_length=2000)
    live_url: Optional[HttpUrl] = None
    repo_url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    status: ProjectStatusLiteral = "live"
    is_featured: bool = False
    sort_order: int = Field(100, ge=0, le=9999)

class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    """PATCH-like: solo campos enviados se actualizan."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1, max_length=20000)
    tech_stack: Optional[str] = Field(None, max_length=2000)
    live_url: Optional[HttpUrl] = None
    repo_url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    status: Optional[ProjectStatusLiteral] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0, le=9999)

class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    visits: int = 0