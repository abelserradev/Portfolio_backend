"""Deterministic scope filter: refuse jailbreaks / off-topic before calling Ollama."""

from __future__ import annotations

import re
import unicodedata

# Short professional refuse — Spanish UX, redirects to portfolio / quote flow
MENSAJE_FUERA_DE_ALCANCE = (
    "Solo puedo ayudarte con proyectos de software de Buildforge: portfolio, "
    "servicios, cotizaciones y contacto. Cuéntame qué quieres construir "
    "(landing, MVP, API, app o integración con IA) y te oriento."
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
    )
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
    "inteligencia artificial",
    "integracion",
    "whatsapp",
    "contacto",
    "email",
    "correo",
    "telefono",
    "proyecto",
    "desarrollo",
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


def es_intento_jailbreak(mensaje: str) -> bool:
    texto = _normalizar(mensaje)
    return any(p.search(texto) for p in _JAILBREAK_PATTERNS)


def tiene_senal_tema_permitido(mensaje: str) -> bool:
    texto = _normalizar(mensaje)
    if _GREETING_RE.search(mensaje) and len(texto) < 80:
        return True
    # Short tokens (ui/api/ia/app/web) must be whole words — "quien" must not match "ui"
    for signal in _TOPIC_SIGNALS:
        if len(signal) <= 3:
            if re.search(rf"\b{re.escape(signal)}\b", texto):
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
    """
    if not mensaje.strip():
        return True
    if es_intento_jailbreak(mensaje):
        return True
    if tiene_senal_tema_permitido(mensaje):
        return False
    return True


def respuesta_viola_politica(respuesta: str) -> bool:
    """Light post-check: oversized or jailbreak-leaking replies get replaced."""
    if len(respuesta) > _MAX_RESPUESTA_SEGURA:
        return True
    lower = _normalizar(respuesta)
    # TODO: tighten once we log false positives from production transcripts
    if "system prompt" in lower or "instrucciones del sistema" in lower:
        return True
    if lower.count("```") >= 2 and len(respuesta) > 400:
        return True
    return False
