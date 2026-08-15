from app.core.config import Settings


def construir_respuesta_sin_llm(
    matriz: dict,
    tipo: str | None,
    rango: str | None,
) -> str:
    """Respuesta determinista cuando Ollama no está en prod (Coolify sin GPU/local)."""
    if tipo and rango:
        rango_data = matriz.get("ranges", {}).get(tipo, {})
        label = rango_data.get("label", "proyecto web")
        semanas = rango_data.get("weeks", "?")
        nota = rango_data.get("notes")
        texto = (
            f"Un buen punto de partida es una {label.lower()}: estimación preliminar {rango}, "
            f"plazo aproximado ~{semanas} semanas."
        )
        if nota:
            texto += f" {nota}."
        texto += (
            " Cuéntame qué quieres lograr (catálogo, contacto, pagos, panel admin) "
            "y te orientamos. También puedes enviar tu solicitud con el formulario del chat."
        )
        return texto

    return (
        "Te ayudamos a definir el alcance paso a paso: qué quieres construir, funciones clave "
        "y plazo. Describe tu idea aquí o envía tu solicitud con el formulario del chat "
        "para que nuestro equipo te evalúe."
    )
