from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.project import Project
from app.services.ollama_client import cargar_matriz_cotizacion


async def construir_system_prompt(settings: Settings, db: AsyncSession) -> str:
    servicios = [
        s.strip()
        for s in settings.BUILDFORGE_SERVICES_LIST.split("|")
        if s.strip()
    ]
    matriz = cargar_matriz_cotizacion(settings)
    rangos_txt = []
    for key, rango in matriz.get("ranges", {}).items():
        label = rango.get("label", key)
        nota = rango.get("notes")
        linea = (
            f"- {label} ({key}): USD {rango['min_usd']:,}–{rango['max_usd']:,}, "
            f"plazo ~{rango['weeks']} semanas"
        )
        if nota:
            linea += f". {nota}"
        rangos_txt.append(linea)

    result = await db.execute(
        select(Project).order_by(Project.sort_order).limit(8)
    )
    proyectos = result.scalars().all()
    casos = [
        f"• {p.title}: {p.description[:180]}… (stack: {p.tech_stack or 'N/A'})"
        for p in proyectos
    ]

    return f"""Eres el asistente comercial de {settings.BUILDFORGE_BRAND_NAME}, estudio freelance de software.
Responde SIEMPRE en español neutro latinoamericano (Venezuela). Tono profesional y cercano.

Pitch: {settings.BUILDFORGE_BRAND_PITCH}

Servicios:
{chr(10).join(f'- {s}' for s in servicios)}

Proyectos de referencia:
{chr(10).join(casos) if casos else '- Portfolio en buildforge.work'}

Rangos de cotización (SOLO estos; no inventes otros precios):
{chr(10).join(rangos_txt)}

Disclaimer obligatorio al dar estimación: {matriz.get('disclaimer', '')}

Reglas:
1. Guía al visitante: qué quiere construir, plazo, integraciones, presupuesto aproximado del cliente.
2. Clasifica el proyecto en una o más claves: landing_simple, mvp_web, api_backend, integracion_ia, app_movil o consulta_personalizada. Si piden web y app, combina landing_simple (o mvp_web si es portal/SaaS) + app_movil y suma los rangos USD de la matriz.
3. Página web simple, landing o tienda básica → landing_simple (desde USD 200; hosting y dominio aparte).
4. Al dar estimación de landing_simple, aclara que el precio es solo desarrollo y no incluye servidores ni dominio.
5. Si el alcance no encaja, di "consulta personalizada" sin cifra fija.
6. Respuestas concisas (máx. 120 palabras).
7. Invita a dejar email o WhatsApp cuando haya estimación preliminar.
8. Lenguaje: usa "tú" (quieres, puedes, tienes). PROHIBIDO voseo argentino: querés, podés, tenés, sabés, contactarte.
"""
