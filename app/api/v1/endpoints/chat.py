from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.common.privacy import enmascarar_email, enmascarar_telefono
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
from app.security.rate_limit import limiter
from app.services.analytics_logger import registrar_evento_analytics
from app.services.chat_service import ChatService
from app.services.ollama_client import OllamaClient

router = APIRouter(prefix="/chat", tags=["chat"])
_settings = get_settings()


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
@limiter.limit(_settings.CHAT_RATE_LIMIT)
async def chat_message(
    request: Request,
    response: Response,
    body: ChatMessageRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatMessageResponse:
    sesion_previa = body.session_id
    es_nueva_sesion = not sesion_previa
    resultado = await service.procesar_mensaje(body.session_id, body.message.strip())
    draft = resultado.get("quote_draft")
    if draft is not None and hasattr(draft, "model_dump"):
        resultado["quote_draft"] = draft

    session_id = str(resultado["session_id"])
    if es_nueva_sesion:
        registrar_evento_analytics(
            "chat.session.started",
            request=request,
            session_id=session_id,
            metadata={"message_chars": len(body.message.strip())},
        )

    meta_mensaje: dict[str, str | int | bool] = {
        "flow_state": str(resultado.get("flow_state", "")),
        "message_chars": len(body.message.strip()),
        "is_new_session": es_nueva_sesion,
        "user_turn": int(resultado.get("user_turn") or 1),
    }
    if draft is not None:
        if getattr(draft, "project_type", None):
            meta_mensaje["project_type"] = str(draft.project_type)
        if getattr(draft, "estimated_range_usd", None):
            meta_mensaje["estimated_range_usd"] = str(draft.estimated_range_usd)
    registrar_evento_analytics(
        "chat.message",
        request=request,
        session_id=session_id,
        metadata=meta_mensaje,
    )

    if resultado.get("flow_state") in ("estimate", "contact"):
        registrar_evento_analytics(
            "chat.form.ready",
            request=request,
            session_id=session_id,
            metadata={"flow_state": str(resultado["flow_state"])},
        )

    return ChatMessageResponse(**resultado)


@router.post("/quote/submit", response_model=QuoteSubmitResponse)
@limiter.limit(_settings.CHAT_RATE_LIMIT)
async def quote_submit(
    request: Request,
    response: Response,
    body: QuoteSubmitRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> QuoteSubmitResponse:
    try:
        resp = await service.enviar_cotizacion(
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

    registrar_evento_analytics(
        "chat.quote.submitted",
        request=request,
        session_id=body.session_id,
        metadata={
            "lead_id": resp.lead_id,
            "channel": body.preferred_channel,
            "email": enmascarar_email(str(body.client_email)),
            "phone": enmascarar_telefono(body.client_phone),
            "description_chars": len(body.project_description.strip()),
            "has_budget": bool((body.client_budget or "").strip()),
            "email_notified": resp.email_notified,
            "whatsapp": body.preferred_channel == "whatsapp",
        },
    )
    return resp
