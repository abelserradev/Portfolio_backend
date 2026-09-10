"""Inferencia de tipos de proyecto y rangos USD desde el mensaje del usuario."""

import re
import unicodedata

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "landing_simple": ("landing", "sitio web simple", "página web", "pagina web", "one page", "tienda"),
    "mvp_web": ("mvp", "web app", "aplicación web", "aplicacion web", "portal", "saas"),
    "api_backend": ("api", "backend", "microservicio", "rest", "graphql"),
    "integracion_ia": ("ia", "inteligencia artificial", "chatbot", "llm", "ocr"),
    "app_movil": ("móvil", "movil", "mobile", "android", "ios", "app nativa", "pwa"),
}

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


def normalizar_texto_chat(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _contiene_palabra_suelta(texto: str, palabra: str) -> bool:
    return bool(re.search(rf"\b{re.escape(palabra)}\b", texto))


def inferir_tipos_proyecto(texto: str) -> list[str]:
    lower = normalizar_texto_chat(texto)
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

    orden = list(_KEYWORDS.keys())
    return [t for t in orden if t in tipos]


def parsear_tipos_guardados(project_type: str | None) -> list[str]:
    if not project_type:
        return []
    return [t.strip() for t in project_type.split(",") if t.strip()]


def fusionar_tipos_proyecto(existentes: list[str], nuevos: list[str]) -> list[str]:
    orden = list(_KEYWORDS.keys())
    merged = list(existentes)
    for tipo in nuevos:
        if tipo not in merged:
            merged.append(tipo)
    merged.sort(key=lambda x: orden.index(x) if x in orden else len(orden))
    return merged


def formatear_rango_usd(clave: str, matriz: dict) -> str | None:
    rango = matriz.get("ranges", {}).get(clave)
    if not rango:
        return None
    return f"USD {rango['min_usd']:,} – {rango['max_usd']:,}"


def formatear_rango_combinado_usd(tipos: list[str], matriz: dict) -> str | None:
    if not tipos:
        return None
    if len(tipos) == 1:
        return formatear_rango_usd(tipos[0], matriz)

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
