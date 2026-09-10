"""Rate limiting por cliente; tras proxy usar cabeceras de IP real."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def identificador_cliente(request: Request) -> str:
    # Coolify / reverse proxy exponen IP real así; primera IP de la lista
    forwarded = (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("True-Client-IP")
        or request.headers.get("x-forwarded-for")
        or request.headers.get("X-Forwarded-For")
    )
    if forwarded:
        return forwarded.split(",", maxsplit=1)[0].strip()
    return get_remote_address(request)


# Una sola instancia: SlowAPIMiddleware solo consulta app.state.limiter
limiter = Limiter(
    key_func=identificador_cliente,
    default_limits=["120/minute"],
    headers_enabled=True,
)
