from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

EventoCliente = Literal[
    "page.load",
    "section.view",
    "nav.click",
    "chat.widget.open",
    "chat.form.visible",
    "cta.click",
]


class AnalyticsEventRequest(BaseModel):
    event: EventoCliente
    visitor_id: str | None = Field(default=None, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)
    section: str | None = Field(default=None, max_length=80)
    cta: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] | None = None

    @field_validator("visitor_id", "session_id", "section", "cta", mode="before")
    @classmethod
    def recortar_texto(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip() or None
        return valor


class AnalyticsEventResponse(BaseModel):
    ok: bool = True
