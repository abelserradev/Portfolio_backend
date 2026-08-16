import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_event_page_load(client: AsyncClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO", logger="buildforge.analytics"):
        resp = await client.post(
            "/api/v1/analytics/event",
            json={
                "event": "page.load",
                "visitor_id": "visitor-test-1",
                "section": "home",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    lineas = [r.message for r in caplog.records if "[analytics]" in r.message]
    assert lineas
    payload = json.loads(lineas[0].split("[analytics] ", 1)[1])
    assert payload["event"] == "page.load"
    assert payload["visitor_id"] == "visitor-test-1"
    assert payload["metadata"]["section"] == "home"


@pytest.mark.asyncio
async def test_analytics_event_invalido_rechazado(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/analytics/event",
        json={"event": "chat.quote.submitted"},
    )
    assert resp.status_code == 422
