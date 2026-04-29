from pydantic import BaseModel

class LanguageStat(BaseModel):
    name: str
    percentage: float
    color: str | None = None
