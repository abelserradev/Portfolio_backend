"""Cabeceras HTTP defensivas; HSTS opcional cuando ya sirves sólo HTTPS."""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class MiddlewareCabecerasSeguridad(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        segundo_hsts: int = 0,
        referrer_policy: str = "strict-origin-when-cross-origin",
    ):
        super().__init__(app)
        self.segundo_hsts = max(0, segundo_hsts)
        self.referrer_policy = referrer_policy

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = self.referrer_policy
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        if self.segundo_hsts > 0:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.segundo_hsts}; includeSubDomains"
            )
        return response
