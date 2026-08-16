from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_chat_service
from app.schemas.chat import (
    ChatConfigResponse,
    ChatHealthResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    QuoteSubmitRequest,
    QuoteSubmitResponse,
)
from app.security.rate_limit import construir_limiter
from app.services.chat_service import ChatService
from app.services.ollama_client import OllamaClient

router = APIRouter(prefix="/chat", tags=["chat"])
_settings = get_settings()
_lim = construir_limiter(_settings.CHAT_RATE_LIMIT)


@router.get("/health", response_model=ChatHealthResponse)
async def chat_health() -> ChatHealthResponse:
    ollama = OllamaClient(_settings)
    ok = await ollama.ping()
    return ChatHealthResponse(ollama="ok" if ok else "unavailable")


@router.get("/config", response_model=ChatConfigResponse)
async def chat_config(
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatConfigResponse:
    return ChatConfigResponse(**service.obtener_config_publica())


@router.post("/message", response_model=ChatMessageResponse)
@_lim.limit(_settings.CHAT_RATE_LIMIT)
async def chat_message(
    request: Request,
    response: Response,
    body: ChatMessageRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatMessageResponse:
    resultado = await service.procesar_mensaje(body.session_id, body.message.strip())
    draft = resultado.get("quote_draft")
    if draft is not None and hasattr(draft, "model_dump"):
        resultado["quote_draft"] = draft
    return ChatMessageResponse(**resultado)


@router.post("/quote/submit", response_model=QuoteSubmitResponse)
@_lim.limit(_settings.CHAT_RATE_LIMIT)
async def quote_submit(
    request: Request,
    response: Response,
    body: QuoteSubmitRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> QuoteSubmitResponse:
    try:
        return await service.enviar_cotizacion(
            session_id=body.session_id,
            client_email=str(body.client_email),
            client_name=body.client_name,
            client_phone=body.client_phone.strip(),
            project_description=body.project_description.strip(),
            client_budget=(body.client_budget or "").strip() or None,
            preferred_channel=body.preferred_channel,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
