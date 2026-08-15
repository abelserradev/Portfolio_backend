import pytest

from app.services.lead_notifier import construir_enlace_whatsapp, formatear_whatsapp_display


def test_formatear_whatsapp_display_venezuela() -> None:
    assert formatear_whatsapp_display("584128034283") == "+58 412-8034283"


def test_construir_enlace_whatsapp_incluye_texto() -> None:
    url = construir_enlace_whatsapp("584128034283", "Hola Buildforge")
    assert url.startswith("https://wa.me/584128034283?text=")
    assert "Hola" in url
