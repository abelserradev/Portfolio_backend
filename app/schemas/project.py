from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=20000)
    tech_stack: Optional[str] = Field(None, max_length=2000)
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