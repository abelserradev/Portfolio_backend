import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from starlette.requests import Request

from app.security.rate_limit import identificador_cliente


def _headers_ip_aislada() -> dict[str, str]:
    # Bucket propio: otros tests de chat comparten 127.0.0.1 y agotan el límite global
    octetos = uuid.uuid4().bytes
    return {"X-Forwarded-For": f"203.0.113.{octetos[0]}.{octetos[1]}"}


def _request_con_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


def test_identificador_cliente_usa_x_forwarded_for() -> None:
    req = _request_con_headers({"X-Forwarded-For": "203.0.113.50, 10.0.0.1"})
    assert identificador_cliente(req) == "203.0.113.50"


def test_identificador_cliente_cf_connecting_ip() -> None:
    req = _request_con_headers(
        {"CF-Connecting-IP": "198.51.100.10", "X-Forwarded-For": "10.0.0.1"}
    )
    assert identificador_cliente(req) == "198.51.100.10"


@pytest.mark.asyncio
async def test_chat_rate_limit_retorna_429(client: AsyncClient) -> None:
    mock_reply = "Respuesta corta de prueba."
    with patch(
        "app.services.ollama_client.OllamaClient.ping",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.ollama_client.OllamaClient.chat",
        new_callable=AsyncMock,
        return_value=mock_reply,
    ):
        headers = _headers_ip_aislada()
        for _ in range(20):
            ok = await client.post(
                "/api/v1/chat/message",
                json={"message": "hola"},
                headers=headers,
            )
            assert ok.status_code == 200

        bloqueado = await client.post(
            "/api/v1/chat/message",
            json={"message": "hola otra vez"},
            headers=headers,
        )
    assert bloqueado.status_code == 429
