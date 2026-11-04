import json
import logging
from datetime import UTC, datetime
from typing import Any

from starlette.requests import Request

from app.core.config import Settings, get_settings
from app.security.rate_limit import identificador_cliente

ANALYTICS_PREFIX = "[analytics]"
_logger = logging.getLogger("buildforge.analytics")

def _ahora_iso() -> str:
    return datetime.now(UTC).isoformat()


def _serializar(valor: Any) -> Any:
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    return str(valor)


def contexto_peticion(request: Request | None) -> dict[str, str]:
    if request is None:
        return {}
    ua = (request.headers.get("user-agent") or "")[:120]
    return {
        "client_ip": identificador_cliente(request),
        "user_agent": ua,
        "referer": (request.headers.get("referer") or "")[:200],
    }


def registrar_evento_analytics(
    evento: str,
    *,
    request: Request | None = None,
    session_id: str | None = None,
    visitor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> None:
    """Log JSON en una línea, grep-eable en Coolify: grep '\\[analytics\\]'."""
    cfg = settings or get_settings()
    if not cfg.ANALYTICS_ENABLED:
        return
    payload: dict[str, Any] = {
        "ts": _ahora_iso(),
        "event": evento,
    }
    if session_id:
        payload["session_id"] = session_id
    if visitor_id:
        payload["visitor_id"] = visitor_id
    payload.update(contexto_peticion(request))
    if metadata:
        payload["metadata"] = {k: _serializar(v) for k, v in metadata.items()}
    _logger.info("%s %s", ANALYTICS_PREFIX, json.dumps(payload, ensure_ascii=False))
