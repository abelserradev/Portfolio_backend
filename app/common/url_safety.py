"""Validación de URLs antes de redirecciones públicas."""

from urllib.parse import urlparse


def es_url_redireccion_segura(url: str) -> bool:
    """Solo https con host — bloquea javascript:, file: y open redirect a esquemas raros."""
    if not url or not url.strip():
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)
