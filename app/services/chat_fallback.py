from app.core.config import Settings


def construir_respuesta_sin_llm(
    matriz: dict,
    tipos: list[str] | None,
    rango: str | None,
) -> str:
    """Respuesta determinista cuando Ollama no está en prod (Coolify sin GPU/local)."""
    if tipos and rango:
        ranges = matriz.get("ranges", {})
        if len(tipos) == 1:
            rango_data = ranges.get(tipos[0], {})
            label = rango_data.get("label", "proyecto web")
            semanas = rango_data.get("weeks", "?")
            nota = rango_data.get("notes")
            texto = (
                f"Un buen punto de partida es una {label.lower()}: estimación preliminar {rango}, "
                f"plazo aproximado ~{semanas} semanas."
            )
            if nota:
                texto += f" {nota}."
        else:
            labels = [ranges.get(t, {}).get("label", t).lower() for t in tipos]
            texto = (
                f"Veo que necesitas {' y '.join(labels)}. "
                f"Estimación preliminar combinada {rango} "
                f"(suma de cada servicio según alcance)."
            )
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
