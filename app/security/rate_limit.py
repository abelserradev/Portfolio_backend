"""Rate limiting por cliente; tras proxy usar X-Forwarded-For."""

from functools import lru_cache

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


@lru_cache
def construir_limiter(limite_global: str) -> Limiter:
    # default_limits aplican si SlowAPIMiddleware está montado sobre la app.
    # headers_enabled permite que el cliente vea Retry-After vía librería
    return Limiter(
        key_func=identificador_cliente,
        default_limits=[limite_global],
        headers_enabled=True,
    )
