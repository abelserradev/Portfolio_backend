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
            "client_phone": "+584121234567",
            "project_description": "Quiero una landing para mi tienda online.",
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
            "client_phone": "+584121234567",
            "project_description": "Necesito un portal web con panel de administración.",
            "preferred_channel": "email",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_quote_submit_whatsapp_incluye_datos_en_url(client: AsyncClient) -> None:
    with patch(
        "app.services.ollama_client.OllamaClient.ping",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.services.lead_notifier.LeadNotifier.notificar_cotizacion",
        new_callable=AsyncMock,
        return_value=False,
    ):
        msg_resp = await client.post(
            "/api/v1/chat/message",
            json={"message": "quiero una landing para mi tienda online"},
        )
        session_id = msg_resp.json()["session_id"]

        resp = await client.post(
            "/api/v1/chat/quote/submit",
            json={
                "session_id": session_id,
                "client_email": "cliente@ejemplo.com",
                "client_name": "María López",
                "client_phone": "+584121234567",
                "project_description": "Landing con catálogo y formulario de contacto.",
                "client_budget": "USD 1,500",
                "preferred_channel": "whatsapp",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["whatsapp_url"].startswith("https://wa.me/")
    assert data["whatsapp_prefill_text"]
    assert "María López" in data["whatsapp_prefill_text"]
    assert "cliente@ejemplo.com" in data["whatsapp_prefill_text"]
    assert "584121234567" in data["whatsapp_prefill_text"]
    assert "Landing con catálogo" in data["whatsapp_prefill_text"]
    assert "USD 1,500" in data["whatsapp_prefill_text"]
    assert "Mar%C3%ADa" in data["whatsapp_url"] or "Maria" in data["whatsapp_url"]
    assert "cliente%40ejemplo.com" in data["whatsapp_url"]
