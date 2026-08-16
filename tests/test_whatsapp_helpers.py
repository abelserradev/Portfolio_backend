import pytest

from app.models.chat import QuoteLead
from app.services.lead_notifier import (
    construir_enlace_whatsapp,
    construir_resumen_whatsapp_lead,
    formatear_whatsapp_display,
)


def test_formatear_whatsapp_display_venezuela() -> None:
    assert formatear_whatsapp_display("584128034283") == "+58 412-8034283"


def test_construir_enlace_whatsapp_incluye_texto() -> None:
    url = construir_enlace_whatsapp("584128034283", "Hola Buildforge")
    assert url.startswith("https://wa.me/584128034283?text=")
    assert "Hola" in url


def test_construir_resumen_whatsapp_lead_incluye_formulario() -> None:
    lead = QuoteLead(
        session_id="sess-1",
        project_type="landing_simple",
        scope_summary="App móvil con pagos en línea",
        estimated_range_usd="USD 200 – 2,000",
        client_name="Juan Pérez",
        client_email="juan@ejemplo.com",
        client_phone="+584129998877",
        client_budget="USD 800",
        preferred_channel="whatsapp",
        status="submitted",
    )
    texto = construir_resumen_whatsapp_lead(lead)
    assert "Juan Pérez" in texto
    assert "App móvil con pagos en línea" in texto
    assert "USD 800" in texto
    assert "juan@ejemplo.com" in texto
    assert "+584129998877" in texto
