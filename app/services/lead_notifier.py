import html
import re
from urllib.parse import quote_plus

import httpx

from app.core.config import Settings
from app.models.chat import QuoteLead
from app.services.ollama_client import cargar_matriz_cotizacion


def formatear_whatsapp_display(e164: str) -> str:
    digits = re.sub(r"\D", "", e164)
    if digits.startswith("58") and len(digits) >= 12:
        return f"+58 {digits[2:5]}-{digits[5:]}"
    return f"+{digits}"


def construir_enlace_whatsapp(e164: str, texto: str) -> str:
    digits = re.sub(r"\D", "", e164)
    return f"https://wa.me/{digits}?text={quote_plus(texto)}"


class LeadNotifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def notificar_cotizacion(self, lead: QuoteLead) -> bool:
        api_key = (self._settings.RESEND_API_KEY or "").strip()
        if not api_key:
            return False

        wa_link = construir_enlace_whatsapp(
            self._settings.BUILDFORGE_WHATSAPP_E164,
            self._resumen_whatsapp(lead),
        )
        admin_ok = await self._enviar_correo(
            api_key,
            destinatarios=[self._settings.RESEND_NOTIFY_TO],
            asunto=f"[Buildforge] Nueva cotización — {lead.client_email}",
            html=self._plantilla_html(lead, wa_link),
        )
        cliente_ok = await self._enviar_correo(
            api_key,
            destinatarios=[str(lead.client_email)],
            asunto="Recibimos tu solicitud de cotización — Buildforge",
            html=self._plantilla_confirmacion_cliente(lead),
        )
        return admin_ok or cliente_ok

    async def _enviar_correo(
        self,
        api_key: str,
        destinatarios: list[str],
        asunto: str,
        html_body: str,
    ) -> bool:
        payload = {
            "from": self._settings.RESEND_FROM_EMAIL,
            "to": destinatarios,
            "subject": asunto,
            "html": html_body,
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
            return True
        except Exception:
            return False

    def _plantilla_confirmacion_cliente(self, lead: QuoteLead) -> str:
        matriz = cargar_matriz_cotizacion(self._settings)
        disclaimer = html.escape(matriz.get("disclaimer", ""))
        nombre = html.escape(lead.client_name or "Cliente")
        rango = html.escape(lead.estimated_range_usd or "A consultar")
        presupuesto = html.escape(lead.client_budget or "No indicado")
        return f"""
        <p>Hola {nombre},</p>
        <p>Recibimos tu solicitud de cotización en Buildforge.</p>
        <p><strong>Estimación preliminar:</strong> {rango}</p>
        <p><strong>Tu presupuesto indicado:</strong> {presupuesto}</p>
        <p>Te contactaremos pronto al correo <strong>{html.escape(str(lead.client_email))}</strong>.</p>
        <p><em>{disclaimer}</em></p>
        """

    def _resumen_whatsapp(self, lead: QuoteLead) -> str:
        nombre = lead.client_name or "Cliente"
        return (
            f"Hola, soy {nombre}. Solicité cotización vía web Buildforge.\n"
            f"Proyecto: {lead.project_type}\n"
            f"Alcance: {lead.scope_summary}\n"
            f"Estimación Buildforge: {lead.estimated_range_usd}\n"
            f"Presupuesto cliente: {lead.client_budget or '—'}\n"
            f"Teléfono: {lead.client_phone or '—'}\n"
            f"Email: {lead.client_email}"
        )

    def _plantilla_html(self, lead: QuoteLead, wa_link: str) -> str:
        matriz = cargar_matriz_cotizacion(self._settings)
        disclaimer = html.escape(matriz.get("disclaimer", ""))
        filas = [
            ("Email", lead.client_email),
            ("Nombre", lead.client_name or "—"),
            ("Teléfono", lead.client_phone or "—"),
            ("Canal preferido", lead.preferred_channel),
            ("Tipo proyecto", lead.project_type),
            ("Estimación Buildforge", lead.estimated_range_usd),
            ("Presupuesto cliente", lead.client_budget or "—"),
        ]
        tbody = "".join(
            f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in filas
        )
        scope = html.escape(lead.scope_summary or "")
        return f"""
        <h2>Nueva cotización Buildforge</h2>
        <table border="1" cellpadding="6">{tbody}</table>
        <p><strong>Alcance:</strong> {scope}</p>
        <p><em>{disclaimer}</em></p>
        <p><a href="{html.escape(wa_link)}">Abrir WhatsApp con el cliente</a></p>
        """
