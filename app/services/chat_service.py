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
from app.services.chat_knowledge import construir_system_prompt
from app.services.lead_notifier import (
    LeadNotifier,
    construir_enlace_whatsapp,
    construir_resumen_whatsapp_lead,
    formatear_whatsapp_display,
)
from app.services.ollama_client import OllamaClient, cargar_matriz_cotizacion

logger = logging.getLogger(__name__)

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "landing_simple": ("landing", "sitio web simple", "página web", "pagina web", "one page", "tienda"),
    "mvp_web": ("mvp", "web app", "aplicación web", "aplicacion web", "portal", "saas"),
    "api_backend": ("api", "backend", "microservicio", "rest", "graphql"),
    "integracion_ia": ("ia", "inteligencia artificial", "chatbot", "llm", "ocr"),
    "app_movil": ("móvil", "movil", "mobile", "android", "ios", "app nativa", "pwa"),
}

# Frases compuestas que anclan un tipo sin mezclar con keywords sueltas ("web", "app")
_PHRASES_POR_TIPO: dict[str, tuple[str, ...]] = {
    "mvp_web": ("web app", "aplicación web", "aplicacion web", "portal", "saas"),
    "landing_simple": (
        "landing",
        "sitio web simple",
        "página web",
        "pagina web",
        "one page",
        "tienda",
    ),
    "api_backend": ("api", "backend", "microservicio", "rest", "graphql"),
    "integracion_ia": ("inteligencia artificial", "chatbot", "llm", "ocr"),
    "app_movil": ("app nativa", "app movil", "app móvil", "pwa"),
}


def _normalizar_texto(texto: str) -> str:
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _contiene_palabra_suelta(texto: str, palabra: str) -> bool:
    return bool(re.search(rf"\b{re.escape(palabra)}\b", texto))


def _inferir_tipos_proyecto(texto: str) -> list[str]:
    """Detecta todos los servicios mencionados; evita quedarse solo con el primer match."""
    lower = _normalizar_texto(texto)
    tipos: list[str] = []

    if any(p in lower for p in _PHRASES_POR_TIPO["mvp_web"]) or _contiene_palabra_suelta(lower, "mvp"):
        tipos.append("mvp_web")
    elif any(p in lower for p in _PHRASES_POR_TIPO["landing_simple"]) or _contiene_palabra_suelta(
        lower, "web"
    ):
        tipos.append("landing_simple")

    quiere_app = (
        any(p in lower for p in _PHRASES_POR_TIPO["app_movil"])
        or _contiene_palabra_suelta(lower, "app")
        or any(p in lower for p in ("android", "ios", "mobile", "movil"))
    )
    if quiere_app and "whatsapp" not in lower:
        tipos.append("app_movil")

    if any(p in lower for p in _PHRASES_POR_TIPO["api_backend"]):
        tipos.append("api_backend")
    if any(p in lower for p in _PHRASES_POR_TIPO["integracion_ia"]) or _contiene_palabra_suelta(
        lower, "ia"
    ):
        tipos.append("integracion_ia")

    # Preservar orden estable de la matriz de precios
    orden = list(_KEYWORDS.keys())
    return [t for t in orden if t in tipos]


def _parsear_tipos_guardados(project_type: str | None) -> list[str]:
    if not project_type:
        return []
    return [t.strip() for t in project_type.split(",") if t.strip()]


def _fusionar_tipos(existentes: list[str], nuevos: list[str]) -> list[str]:
    orden = list(_KEYWORDS.keys())
    merged = list(existentes)
    for tipo in nuevos:
        if tipo not in merged:
            merged.append(tipo)
    merged.sort(key=lambda x: orden.index(x) if x in orden else len(orden))
    return merged


def _formatear_rango(clave: str, matriz: dict) -> str | None:
    rango = matriz.get("ranges", {}).get(clave)
    if not rango:
        return None
    return f"USD {rango['min_usd']:,} – {rango['max_usd']:,}"


def _formatear_rango_combinado(tipos: list[str], matriz: dict) -> str | None:
    if not tipos:
        return None
    if len(tipos) == 1:
        return _formatear_rango(tipos[0], matriz)

    ranges = matriz.get("ranges", {})
    min_total = 0
    max_total = 0
    for tipo in tipos:
        rango = ranges.get(tipo)
        if not rango:
            continue
        min_total += rango["min_usd"]
        max_total += rango["max_usd"]
    if min_total <= 0:
        return None
    return f"USD {min_total:,} – {max_total:,}"


def _avanzar_estado(actual: ChatFlowState, mensaje: str) -> ChatFlowState:
    if actual == ChatFlowState.GREETING:
        return ChatFlowState.DISCOVERY
    if actual == ChatFlowState.DISCOVERY and len(mensaje.strip()) > 12:
        return ChatFlowState.SCOPE
    if actual == ChatFlowState.SCOPE:
        return ChatFlowState.ESTIMATE
    if actual == ChatFlowState.ESTIMATE:
        return ChatFlowState.CONTACT
    return actual


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
        tipos_nuevos = _inferir_tipos_proyecto(mensaje)
        tipos_previos = _parsear_tipos_guardados(chat_session.project_type)
        tipos = _fusionar_tipos(tipos_previos, tipos_nuevos) if tipos_nuevos else tipos_previos
        if tipos:
            chat_session.project_type = ",".join(tipos)
            rango = _formatear_rango_combinado(tipos, matriz)
            if rango:
                chat_session.estimated_range_usd = rango

        if not chat_session.scope_summary and len(mensaje) > 20:
            chat_session.scope_summary = mensaje[:500]

        estado = ChatFlowState(chat_session.flow_state)
        nuevo_estado = _avanzar_estado(estado, mensaje)
        chat_session.flow_state = nuevo_estado.value

        system_prompt = await construir_system_prompt(self._settings, self._db)
        mensajes_ollama = [{"role": "system", "content": system_prompt}, *historial]

        wa_url_resp: str | None = None
        wa_display_resp: str | None = None

        # Atajo: enlace WhatsApp sin depender del LLM
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
                    logger.warning("Ollama chat falló (%s), usando respuesta por reglas", type(exc).__name__)
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

        matriz = cargar_matriz_cotizacion(self._settings)
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
