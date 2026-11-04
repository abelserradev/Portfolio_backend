from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.chat import QuoteLead
from app.services.lead_notifier import LeadNotifier


@pytest.mark.asyncio
async def test_notificar_cotizacion_posts_html_body_to_resend() -> None:
    settings = Settings(
        RESEND_API_KEY="re_test_key_not_real",
        RESEND_FROM_EMAIL="onboarding@resend.dev",
        RESEND_NOTIFY_TO="admin@example.com",
        BUILDFORGE_WHATSAPP_E164="584128034283",
    )
    lead = QuoteLead(
        session_id="11111111-1111-1111-1111-111111111111",
        project_type="landing_simple",
        scope_summary="Landing de prueba",
        estimated_range_usd="USD 500 – 1,500",
        client_name="Abel",
        client_email="cliente@example.com",
        client_phone="+584120000000",
        preferred_channel="email",
        status="submitted",
    )
    notifier = LeadNotifier(settings)

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.lead_notifier.httpx.AsyncClient", return_value=mock_client):
        ok = await notifier.notificar_cotizacion(lead)

    assert ok is True
    assert mock_client.post.await_count == 2
    first_json = mock_client.post.await_args_list[0].kwargs["json"]
    assert first_json["to"] == ["admin@example.com"]
    assert "html" in first_json
    assert "Nueva cotización" in first_json["html"]
