from typing import Annotated

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.schemas.analytics import AnalyticsEventRequest, AnalyticsEventResponse
from app.security.rate_limit import limiter
from app.services.analytics_logger import registrar_evento_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])
_settings = get_settings()


@router.post("/event", response_model=AnalyticsEventResponse)
@limiter.limit(_settings.ANALYTICS_RATE_LIMIT)
async def registrar_evento_cliente(
    request: Request,
    response: Response,
    body: AnalyticsEventRequest,
) -> AnalyticsEventResponse:
    meta: dict[str, str | int | bool] = {}
    if body.section:
        meta["section"] = body.section
    if body.cta:
        meta["cta"] = body.cta
    if body.metadata:
        for clave, valor in body.metadata.items():
            if isinstance(valor, (str, int, float, bool)) and len(str(valor)) <= 200:
                meta[str(clave)[:40]] = valor

    registrar_evento_analytics(
        body.event,
        request=request,
        session_id=body.session_id,
        visitor_id=body.visitor_id,
        metadata=meta or None,
    )
    return AnalyticsEventResponse()
