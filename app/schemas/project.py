from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class ProjectBase(BaseModel):
    title: str
    description: str
    tech_stack: Optional[str] = None
    live_url: Optional[HttpUrl] = None
    repo_url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    visits: int = 0

    class Config:
        from_attributes = True