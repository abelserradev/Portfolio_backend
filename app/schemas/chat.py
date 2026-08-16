from pydantic import BaseModel, EmailStr, Field


class ChatMessageRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=36)
    message: str = Field(min_length=1, max_length=2000)


class QuoteDraftResponse(BaseModel):
    project_type: str | None = None
    scope_summary: str | None = None
    estimated_range_usd: str | None = None
    disclaimer: str | None = None


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str
    flow_state: str
    quote_draft: QuoteDraftResponse | None = None
    whatsapp_url: str | None = None
    whatsapp_display: str | None = None


class QuoteSubmitRequest(BaseModel):
    session_id: str = Field(min_length=36, max_length=36)
    client_email: EmailStr
    client_name: str | None = Field(default=None, max_length=200)
    client_phone: str = Field(min_length=6, max_length=32)
    project_description: str = Field(min_length=10, max_length=2000)
    client_budget: str | None = Field(default=None, max_length=64)
    preferred_channel: str = Field(default="email", pattern="^(email|whatsapp)$")


class QuoteSubmitResponse(BaseModel):
    lead_id: int
    status: str
    whatsapp_url: str | None = None
    whatsapp_prefill_text: str | None = None
    whatsapp_display: str | None = None
    email_notified: bool = False


class ChatHealthResponse(BaseModel):
    ollama: str


class ChatConfigResponse(BaseModel):
    whatsapp_display: str
    whatsapp_e164: str
    disclaimer: str
    brand_name: str
