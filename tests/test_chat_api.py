from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_message_genera_session_id(client: AsyncClient) -> None:
    mock_reply = "Ofrecemos apps web, APIs e integraciones con IA."
    with patch(
        "app.services.ollama_client.OllamaClient.ping",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.ollama_client.OllamaClient.chat",
        new_callable=AsyncMock,
        return_value=mock_reply,
    ):
        resp = await client.post(
            "/api/v1/chat/message",
            json={"message": "¿Qué servicios tienen?"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"]
    assert mock_reply in data["reply"]


@pytest.mark.asyncio
async def test_chat_message_whatsapp_devuelve_url_sin_texto_crudo(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/chat/message",
        json={"message": "tienes contacto por whatsapp?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["whatsapp_url"]
    assert data["whatsapp_url"].startswith("https://wa.me/")
    assert "https://wa.me/" not in data["reply"]
    assert data["whatsapp_display"]


@pytest.mark.asyncio
async def test_chat_message_fallback_sin_ollama(client: AsyncClient) -> None:
    with patch(
        "app.services.ollama_client.OllamaClient.ping",
        new_callable=AsyncMock,
        return_value=False,
    ):
        resp = await client.post(
            "/api/v1/chat/message",
            json={"message": "hola quiero hacer una pagina web para mi tienda"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "El asistente IA no respondió" not in data["reply"]
    assert data["quote_draft"] is not None
    assert "200" in (data["quote_draft"].get("estimated_range_usd") or "")


@pytest.mark.asyncio
async def test_quote_submit_email_invalido(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/chat/quote/submit",
        json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "client_email": "no-es-email",
            "preferred_channel": "email",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_quote_submit_sesion_inexistente(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/chat/quote/submit",
        json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "client_email": "cliente@ejemplo.com",
            "preferred_channel": "email",
        },
    )
    assert resp.status_code == 404
