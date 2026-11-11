from app.services.chat_sanitize import (
    sanitizar_mensaje_usuario,
    sanitizar_respuesta_asistente,
)
from app.services.chat_scope_guard import (
    debe_rechazar_antes_de_llm,
    respuesta_viola_politica,
)


def test_sanitizar_script_tag_y_handlers() -> None:
    crudo = '<script>alert("xss")</script> onclick=alert(1) quiero landing'
    limpio = sanitizar_mensaje_usuario(crudo)
    assert "<script" not in limpio.casefold()
    assert "onclick" not in limpio.casefold()
    assert "landing" in limpio.casefold()


def test_sanitizar_javascript_y_data_urls() -> None:
    crudo = "ver javascript:alert(1) y data:text/html,hi para mi MVP"
    limpio = sanitizar_mensaje_usuario(crudo)
    assert "javascript:" not in limpio.casefold()
    assert "data:" not in limpio.casefold()
    assert "mvp" in limpio.casefold()


def test_sanitizar_null_y_control_chars() -> None:
    crudo = "hola\x00\x01 mundo\nnecesito API"
    limpio = sanitizar_mensaje_usuario(crudo)
    assert "\x00" not in limpio
    assert "\x01" not in limpio
    assert "API" in limpio or "api" in limpio.casefold()


def test_sanitizar_entidades_html_script() -> None:
    crudo = "&lt;script&gt;alert(1)&lt;/script&gt; cotizar landing"
    limpio = sanitizar_mensaje_usuario(crudo)
    assert "<script" not in limpio.casefold()
    assert "<" not in limpio and ">" not in limpio
    assert "landing" in limpio.casefold()


def test_sanitizar_preserva_espanol() -> None:
    limpio = sanitizar_mensaje_usuario("¿Cuánto cuesta una página web?")
    assert "Cuánto" in limpio or "cuánto" in limpio.casefold()
    assert "página" in limpio or "pagina" in limpio.casefold()


def test_script_solo_queda_fuera_de_alcance() -> None:
    limpio = sanitizar_mensaje_usuario("<script>alert(1)</script>")
    assert debe_rechazar_antes_de_llm(limpio)


def test_sanitizar_respuesta_quita_script() -> None:
    crudo = 'Estimación USD 200 <script>document.cookie</script> para landing.'
    limpio = sanitizar_respuesta_asistente(crudo)
    assert "<script" not in limpio.casefold()
    assert "document.cookie" in limpio or "landing" in limpio.casefold()


def test_leak_system_prompt_outbound() -> None:
    leak = (
        "Eres el asistente de taller de Buildforge, estudio que trata el software "
        "como patrones. Rangos de cotización (SOLO estos; no inventes otros precios):"
    )
    assert respuesta_viola_politica(sanitizar_respuesta_asistente(leak))
