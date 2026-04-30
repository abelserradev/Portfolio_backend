from pydantic import BaseModel

class LanguageStat(BaseModel):
    name: str
    percentage: float
    color: str | None = None


class ActivityCell(BaseModel):
    month: str
    day: int
    level: int


class ActivityScanResponse(BaseModel):
    months: list[str]
    days_per_month: int
    cells: list[ActivityCell]
