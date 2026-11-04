"""Inbound/outbound chat sanitation — neutralize XSS and control-char abuse before LLM."""

from __future__ import annotations

import html
import re

# Keep Spanish letters/punctuation; drop C0 controls except tab/LF/CR (normalized later)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>", re.IGNORECASE)
_EVENT_HANDLER_RE = re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE)
_JS_PROTOCOL_RE = re.compile(r"javascript\s*:", re.IGNORECASE)
_DATA_PROTOCOL_RE = re.compile(r"data\s*:", re.IGNORECASE)
_SCRIPT_FRAGMENT_RE = re.compile(r"<\s*/?\s*script\b[^>]*>", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
_MULTILINE_BLANK_RE = re.compile(r"\n{3,}")


def sanitizar_mensaje_usuario(mensaje: str) -> str:
    """Strip HTML/script payloads and dangerous protocols; collapse noisy whitespace.

    Runs before scope/jailbreak checks so delimiter tricks hidden in tags still get caught
    after tags are removed. Spanish accents and punctuation are preserved.
    """
    if not mensaje:
        return ""
    texto = mensaje.replace("\x00", "")
    texto = _CONTROL_RE.sub("", texto)
    # Decode entities once so &lt;script&gt; cannot bypass the tag strip
    texto = html.unescape(texto)
    texto = _SCRIPT_FRAGMENT_RE.sub(" ", texto)
    texto = _HTML_TAG_RE.sub(" ", texto)
    texto = _EVENT_HANDLER_RE.sub("", texto)
    texto = _JS_PROTOCOL_RE.sub("", texto)
    texto = _DATA_PROTOCOL_RE.sub("", texto)
    # Neutralize leftover angle brackets that often mark injected markup
    texto = texto.replace("<", " ").replace(">", " ")
    texto = _WHITESPACE_RE.sub(" ", texto)
    texto = _MULTILINE_BLANK_RE.sub("\n\n", texto)
    return texto.strip()


def sanitizar_respuesta_asistente(respuesta: str) -> str:
    """Strip script/HTML from model output before returning to the client."""
    if not respuesta:
        return ""
    texto = respuesta.replace("\x00", "")
    texto = _CONTROL_RE.sub("", texto)
    texto = html.unescape(texto)
    texto = _SCRIPT_FRAGMENT_RE.sub(" ", texto)
    texto = _HTML_TAG_RE.sub(" ", texto)
    texto = _EVENT_HANDLER_RE.sub("", texto)
    texto = _JS_PROTOCOL_RE.sub("", texto)
    texto = _DATA_PROTOCOL_RE.sub("", texto)
    texto = texto.replace("<", " ").replace(">", " ")
    texto = _WHITESPACE_RE.sub(" ", texto)
    return texto.strip()
