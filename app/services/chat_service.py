import json
import logging
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.chat import ChatSession, QuoteLead
from app.models.chat_enums import ChatFlowState, PreferredChannel, QuoteLeadStatus
from app.repositories.chat import ChatRepository
from app.schemas.chat import QuoteDraftResponse, QuoteSubmitResponse
from app.services.chat_fallback import construir_respuesta_sin_llm
from app.services.chat_flow_state import avanzar_estado_flujo_chat
from app.services.chat_knowledge import construir_system_prompt
from app.services.chat_type_inference import (
    formatear_rango_combinado_usd,
    fusionar_tipos_proyecto,
    inferir_tipos_proyecto,
    parsear_tipos_guardados,
)
from app.services.lead_notifier import (
    LeadNotifier,
    construir_enlace_whatsapp,
    construir_resumen_whatsapp_lead,
    formatear_whatsapp_display,
)
from app.services.ollama_client import OllamaClient, cargar_matriz_cotizacion

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        settings: Settings,
        db: AsyncSession,
        ollama: OllamaClient,
        notifier: LeadNotifier,
    ) -> None:
        self._settings = settings
        self._db = db
        self._ollama = ollama
        self._notifier = notifier
        self._repo = ChatRepository(db)

    async def procesar_mensaje(self, session_id: str | None, mensaje: str) -> dict:
        chat_session = await self._obtener_o_crear_sesion(session_id)
        historial: list[dict[str, str]] = json.loads(chat_session.messages_json or "[]")
        historial.append({"role": "user", "content": mensaje})

        matriz = cargar_matriz_cotizacion(self._settings)
        tipos_nuevos = inferir_tipos_proyecto(mensaje)
        tipos_previos = parsear_tipos_guardados(chat_session.project_type)
        tipos = fusionar_tipos_proyecto(tipos_previos, tipos_nuevos) if tipos_nuevos else tipos_previos
        if tipos:
            chat_session.project_type = ",".join(tipos)
            rango = formatear_rango_combinado_usd(tipos, matriz)
            if rango:
                chat_session.estimated_range_usd = rango

        if not chat_session.scope_summary and len(mensaje) > 20:
            chat_session.scope_summary = mensaje[:500]

        estado = ChatFlowState(chat_session.flow_state)
        chat_session.flow_state = avanzar_estado_flujo_chat(estado, mensaje).value

        system_prompt = await construir_system_prompt(self._settings, self._db)
        mensajes_ollama = [{"role": "system", "content": system_prompt}, *historial]

        wa_url_resp: str | None = None
        wa_display_resp: str | None = None

        if any(p in mensaje.casefold() for p in ("whatsapp", "wa.me", "enlace de whatsapp")):
            wa_url_resp = construir_enlace_whatsapp(
                self._settings.BUILDFORGE_WHATSAPP_E164,
                "Hola Buildforge, quiero cotizar un proyecto web.",
            )
            wa_display_resp = formatear_whatsapp_display(self._settings.BUILDFORGE_WHATSAPP_E164)
            reply = (
                f"Claro. Escríbenos por WhatsApp al {wa_display_resp}.\n\n"
                "También puedes usar el formulario de cotización aquí en el chat."
            )
        else:
            ollama_disponible = await self._ollama.ping()
            if not ollama_disponible:
                logger.warning("Chat sin LLM: Ollama no disponible, usando respuesta por reglas")
                reply = construir_respuesta_sin_llm(matriz, tipos, chat_session.estimated_range_usd)
            else:
                try:
                    reply = await self._ollama.chat(mensajes_ollama)
                except Exception as exc:
                    logger.warning(
                        "Ollama chat falló (%s), usando respuesta por reglas",
                        type(exc).__name__,
                    )
                    reply = construir_respuesta_sin_llm(matriz, tipos, chat_session.estimated_range_usd)

        historial.append({"role": "assistant", "content": reply})
        chat_session.messages_json = json.dumps(historial[-20:], ensure_ascii=False)
        await self._repo.guardar_sesion(chat_session)
        await self._db.commit()

        turnos_usuario = sum(1 for m in historial if m.get("role") == "user")

        draft = None
        if chat_session.estimated_range_usd or chat_session.project_type:
            draft = QuoteDraftResponse(
                project_type=chat_session.project_type,
                scope_summary=chat_session.scope_summary,
                estimated_range_usd=chat_session.estimated_range_usd,
                disclaimer=matriz.get("disclaimer"),
            )

        return {
            "session_id": chat_session.session_id,
            "reply": reply,
            "flow_state": chat_session.flow_state,
            "quote_draft": draft,
            "whatsapp_url": wa_url_resp,
            "whatsapp_display": wa_display_resp,
            "user_turn": turnos_usuario,
        }

    async def enviar_cotizacion(
        self,
        session_id: str,
        client_email: str,
        client_name: str | None,
        client_phone: str,
        project_description: str,
        client_budget: str | None,
        preferred_channel: str,
    ) -> QuoteSubmitResponse:
        chat_session = await self._repo.obtener_sesion(session_id)
        if chat_session is None:
            raise ValueError("Sesión no encontrada")

        lead = QuoteLead(
            session_id=session_id,
            project_type=chat_session.project_type or "consulta_personalizada",
            scope_summary=project_description,
            estimated_range_usd=chat_session.estimated_range_usd or "A consultar",
            client_name=client_name,
            client_email=str(client_email),
            client_phone=client_phone,
            client_budget=client_budget,
            preferred_channel=preferred_channel,
            status=QuoteLeadStatus.SUBMITTED.value,
        )
        lead = await self._repo.crear_lead(lead)
        chat_session.flow_state = ChatFlowState.SUBMITTED.value
        await self._repo.guardar_sesion(chat_session)

        notificado = False
        try:
            notificado = await self._notifier.notificar_cotizacion(lead)
        except Exception:
            notificado = False

        if notificado:
            lead.status = QuoteLeadStatus.NOTIFIED.value
            await self._repo.actualizar_lead(lead)

        await self._db.commit()

        wa_url = None
        wa_prefill: str | None = None
        wa_display = formatear_whatsapp_display(self._settings.BUILDFORGE_WHATSAPP_E164)
        if preferred_channel == PreferredChannel.WHATSAPP.value:
            wa_prefill = construir_resumen_whatsapp_lead(lead)
            wa_url = construir_enlace_whatsapp(
                self._settings.BUILDFORGE_WHATSAPP_E164,
                wa_prefill,
            )

        return QuoteSubmitResponse(
            lead_id=lead.id,
            status=lead.status,
            whatsapp_url=wa_url,
            whatsapp_prefill_text=wa_prefill,
            whatsapp_display=wa_display,
            email_notified=notificado,
        )

    async def _obtener_o_crear_sesion(self, session_id: str | None) -> ChatSession:
        if session_id:
            existente = await self._repo.obtener_sesion(session_id)
            if existente is not None:
                return existente
        nueva = ChatSession(session_id=str(uuid.uuid4()))
        return await self._repo.guardar_sesion(nueva)

    def obtener_config_publica(self) -> dict:
        matriz = cargar_matriz_cotizacion(self._settings)
        e164 = re.sub(r"\D", "", self._settings.BUILDFORGE_WHATSAPP_E164)
        return {
            "whatsapp_display": formatear_whatsapp_display(e164),
            "whatsapp_e164": e164,
            "disclaimer": matriz.get("disclaimer", ""),
            "brand_name": self._settings.BUILDFORGE_BRAND_NAME,
        }
