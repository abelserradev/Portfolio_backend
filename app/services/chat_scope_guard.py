"""Deterministic scope filter: refuse jailbreaks / off-topic before calling Ollama."""

from __future__ import annotations

import re
import unicodedata

# Short professional refuse — Spanish UX, redirects to portfolio / quote flow
MENSAJE_FUERA_DE_ALCANCE = (
    "Solo puedo ayudarte con el taller Buildforge: portfolio, servicios, "
    "cotizaciones y contacto. Cuéntame qué quieres construir "
    "(landing, MVP, API, app o integración con IA) y te oriento."
)

# FAQ: "qué es Buildforge" must never hit the generic refuse (false positive / LLM parrot)
MENSAJE_IDENTIDAD_BUILDFORGE = (
    "Buildforge es la marca y el dominio de un desarrollador fullstack: "
    "un taller de patrones donde el portafolio muestra proyectos de software "
    "(apps web, APIs, móvil e integraciones con IA) listos para fundirse en "
    "producto. Aquí puedes revisar esos trabajos, los servicios y pedir una "
    "cotización orientativa. Este chat ayuda a acotar presupuesto y contacto; "
    "no sustituye el email ni los canales del sitio."
)

# FAQ: status labels on mission plates (EN PRODUCCIÓN / EN DESARROLLO / …)
MENSAJE_ESTADO_MISION = (
    "En las placas de misiones del portafolio, esas etiquetas indican el estado "
    "de cada proyecto:\n"
    "• EN PRODUCCIÓN: ya está publicado y puedes abrirlo con el enlace de la placa.\n"
    "• EN DESARROLLO: aún se construye o despliega; el acceso público puede no estar listo.\n"
    "• MVP ACTIVO: hay una demo usable mientras el producto sigue evolucionando.\n"
    "• PRÓXIMAMENTE: anunciado, todavía sin demo pública.\n"
    "Si te interesa uno en concreto, dime el nombre y te oriento o cotizamos algo similar."
)

_MAX_RESPUESTA_SEGURA = 900

_JAILBREAK_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?",
        r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|rules?)",
        r"forget\s+(all\s+)?(your\s+)?(instructions?|rules?|prompt)",
        r"ignora(r)?\s+(todas\s+)?(las\s+)?(instrucciones|reglas|indicaciones)",
        r"olvida(r)?\s+(todas\s+)?(las\s+)?(instrucciones|reglas)",
        r"\bdan\b.{0,40}\b(mode|jailbreak)\b",
        r"\bjailbreak\b",
        r"developer\s+mode",
        r"act\s+as\s+(an?\s+)?unrestricted",
        r"act[uá]a\s+como\s+(una?\s+)?ia\s+sin\s+restricciones",
        r"you\s+are\s+now\s+(a|an|dan|unrestricted)",
        r"pretend\s+(you\s+have\s+)?no\s+restrictions?",
        r"reveal\s+(your\s+)?(system\s+)?prompt",
        r"show\s+(me\s+)?(your\s+)?(system\s+)?prompt",
        r"revela(r)?\s+(el\s+)?(system\s+)?prompt",
        r"muestra(me)?\s+(el\s+)?(system\s+)?prompt",
        r"print\s+(your\s+)?system\s+prompt",
        r"bypass\s+(your\s+)?(safety|filters?|rules?)",
        r"sin\s+restricciones?\s+(eticas|éticas|de\s+seguridad)?",
        r"roleplay\s+as\s+(an?\s+)?(unrestricted|uncensored)",
        # Delimiter / role spoofing used to hijack chat templates
        r"#{2,}\s*system\b",
        r"\[inst\]",
        r"<<\s*sys\s*>>",
        r"</\s*s\s*>",
        r"<\|?\s*(system|assistant|user)\s*\|?>",
        r"^\s*system\s*:",
        r"^\s*assistant\s*:",
        r"\bsystem\s*:\s*(you are|eres|ignore|olvid)",
        r"\bassistant\s*:\s*(sure|of course|claro|aqui|aquí)",
        r"new\s+instructions?",
        r"nuevas?\s+instrucciones?",
        r"\boverride\b.{0,40}\b(instructions?|rules?|prompt|system)\b",
        r"\bexfiltrat(e|ion|ar)\b",
        r"repeat\s+(your|the)\s+(system\s+)?(prompt|instructions?|rules?)",
        r"repite\s+(tu|el)\s+(system\s+)?(prompt|instrucciones?|reglas?)",
        r"encode\s+(your|the)\s+(system\s+)?(prompt|instructions?)",
        r"codifica(r)?\s+(tus?\s+|el\s+)?(instrucciones?|prompt|reglas?)",
        r"base64\s*(decode|encode|decodifica|codifica)",
        r"decode\s+.{0,20}base64",
        r"output\s+(your\s+)?(hidden\s+)?(system\s+)?(prompt|instructions?)",
    )
)

# Verbatim fragments from construir_system_prompt — leak ⇒ refuse outbound
_PROMPT_LEAK_MARKERS: tuple[str, ...] = (
    "eres el asistente de taller",
    "rangos de cotizacion",
)

_OFFTOPIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(poema|poem|poesía|poetry|haiku|soneto)\b",
        r"\b(receta|recipe|cocinar|cocina|baking)\b",
        r"\b(tarea|homework|ensayo|essay)\b.{0,30}\b(escuela|colegio|universidad|school|college)\b",
        r"\b(pol[ií]tica|politics|elecciones|election)\b",
        r"\b(diagn[oó]stico|medical advice|consejo m[eé]dico|receta m[eé]dica)\b",
        r"\b(asesor[ií]a legal|legal advice|demanda judicial)\b",
        r"c[oó]mo\s+hacke(ar|o)\b",
        r"\b(hackear|crackear|piratear)\b.{0,40}\b(wifi|wi-?fi|contrase[nñ]a|password|cuenta)\b",
        r"escribe(me)?\s+(un|una)\s+(cuento|chiste|canci[oó]n|letra)\b",
        r"write\s+(me\s+)?(a\s+)?(poem|story|song|joke)\b",
        r"genera(me)?\s+(un|una)\s+(poema|receta|chiste)\b",
        r"\b(credenciales|api[_ ]?keys?|secret[_ ]?key|password\s+de\s+producci[oó]n)\b",
    )
)

_TOPIC_SIGNALS: tuple[str, ...] = (
    "buildforge",
    "portfolio",
    "cotiz",
    "presupuesto",
    "precio",
    "costo",
    "cuesta",
    "servicio",
    "landing",
    "mvp",
    "saas",
    "api",
    "backend",
    "frontend",
    "app",
    "movil",
    "mobile",
    "android",
    "ios",
    "pwa",
    "web",
    "sitio",
    "pagina",
    "portal",
    "tienda",
    "ecommerce",
    "chatbot",
    "llm",
    "ocr",
    "ia",
    "inteligencia artificial",
    "integracion",
    "whatsapp",
    "contacto",
    "email",
    "correo",
    "telefono",
    "proyecto",
    "desarrollo",
    "produccion",
    "mision",
    "etiqueta",
    "software",
    "stack",
    "react",
    "next",
    "nestjs",
    "django",
    "fastapi",
    "hosting",
    "dominio",
    "ui",
    "ux",
    "dashboard",
    "panel",
    "microservicio",
    "graphql",
    "rest",
)

_GREETING_RE = re.compile(
    r"^\s*(hola|buenas|buen[oa]s?\s+(d[ií]as|tardes|noches)|hey|hi|hello|"
    r"saludos|qu[eé]\s+tal|c[oó]mo\s+est[aá]s?)\b",
    re.IGNORECASE,
)


def _normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def mensaje_rechazo_fuera_de_alcance() -> str:
    return MENSAJE_FUERA_DE_ALCANCE


def mensaje_identidad_buildforge() -> str:
    return MENSAJE_IDENTIDAD_BUILDFORGE


def mensaje_estado_mision() -> str:
    return MENSAJE_ESTADO_MISION


def es_pregunta_estado_mision(mensaje: str) -> bool:
    """True when the user asks what portfolio card badges mean (EN PRODUCCIÓN, etc.)."""
    texto = _normalizar(mensaje)
    if not texto.strip():
        return False
    pregunta = any(
        p in texto
        for p in (
            "que significa",
            "que quiere decir",
            "significa",
            "quiere decir",
            "diferencia entre",
            "que es en ",
            "etiqueta",
            "badge",
            "estado de",
            "estado del",
        )
    )
    if not pregunta:
        return False
    return any(
        e in texto
        for e in (
            "en produccion",
            "en desarrollo",
            "mvp activo",
            "proximamente",
            "en curso",
            "produccion",
            "mvp",
        )
    )


def es_pregunta_identidad_buildforge(mensaje: str) -> bool:
    """True for brand/portfolio identity questions — answer with canned copy, skip refuse/LLM."""
    texto = _normalizar(mensaje)
    if not texto.strip():
        return False
    # Direct "qué es / quién es / qué hace Buildforge"
    if "buildforge" in texto and any(
        p in texto
        for p in (
            "que es",
            "quien es",
            "que hace",
            "que significa",
            "sobre",
            "acerca de",
            "marca",
            "dominio",
            "portafolio",
            "portfolio",
            "estudio",
            "empresa",
        )
    ):
        return True
    # Assistant self-intro without naming the brand
    if any(
        p in texto
        for p in (
            "quien eres",
            "que eres",
            "que es esto",
            "sobre ti",
            "hablame de ti",
            "cuentame de ti",
            "para que sirve este chat",
        )
    ):
        return True
    return False


def es_intento_jailbreak(mensaje: str) -> bool:
    texto = _normalizar(mensaje)
    return any(p.search(texto) for p in _JAILBREAK_PATTERNS)


def tiene_senal_tema_permitido(mensaje: str) -> bool:
    texto = _normalizar(mensaje)
    if _GREETING_RE.search(mensaje) and len(texto) < 80:
        return True
    # Pad tokens so short signals (ia/ui/api) are whole words — "quien" must not match "ui"
    padded = " " + re.sub(r"[^\w]+", " ", texto, flags=re.UNICODE) + " "
    for signal in _TOPIC_SIGNALS:
        if len(signal) <= 3:
            if f" {signal} " in padded:
                return True
        elif signal in texto:
            return True
    return False


def es_claramente_fuera_de_tema(mensaje: str) -> bool:
    """Legacy blocklist helper; keep for explicit known-bad patterns in tests."""
    if tiene_senal_tema_permitido(mensaje):
        return False
    texto = _normalizar(mensaje)
    return any(p.search(texto) for p in _OFFTOPIC_PATTERNS)


def debe_rechazar_antes_de_llm(mensaje: str) -> bool:
    """Allowlist: only greetings + Buildforge/project signals reach Ollama.

    Trivia like "qué es Google" has no topic signal → refuse (blocklist alone was too weak).
    Brand/status FAQ questions are never refused here (canned answer upstream).
    """
    if not mensaje.strip():
        return True
    if es_pregunta_identidad_buildforge(mensaje) or es_pregunta_estado_mision(mensaje):
        return False
    if es_intento_jailbreak(mensaje):
        return True
    if tiene_senal_tema_permitido(mensaje):
        return False
    return True


def respuesta_viola_politica(respuesta: str) -> bool:
    """Light post-check: oversized, leaked system prompt, or jailbreak-shaped replies."""
    if len(respuesta) > _MAX_RESPUESTA_SEGURA:
        return True
    lower = _normalizar(respuesta)
    # TODO: tighten once we log false positives from production transcripts
    if "system prompt" in lower or "instrucciones del sistema" in lower:
        return True
    if any(marker in lower for marker in _PROMPT_LEAK_MARKERS):
        return True
    if lower.count("```") >= 2 and len(respuesta) > 400:
        return True
    return False
