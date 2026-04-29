"""
Arranque de esquema y proyectos ejemplo del portfolio sin migraciones Alembic.

Cada proyecto del catálogo se inserta si aún no existe: con ``live_url`` se busca
por URL; si es ``None`` (despliegue pendiente), se usa el título exacto más
``live_url IS NULL``. Para la quiniela, si el título del catálogo cambió respecto
a filas antiguas, se reutiliza la primera fila que coincida por patrón (evita
duplicados al renombrar). Tras sincronizar, se eliminan filas duplicadas de
quiniela conservando el ``id`` más bajo.

Las filas del catálogo se reconcilian (título, descripción, tech_stack,
``live_url``) al arrancar para propagar cambios sin duplicados.
"""

from sqlalchemy import select

from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models.project import Project

# Cuarto elemento: ``live_url`` o ``None`` si aún no hay URL de producción.
_SEMILLAS: tuple[tuple[str, str, str, str | None], ...] = (
    (
        "Condominio BuildForge · recibos y cobros",
        (
            "Portal para administración del condominio: la administración emite "
            "y gestiona recibos y cobros; los propietarios consultan deudas, "
            "reportan pagos adjuntando comprobantes y visualizan el estado "
            "(pendientes, aprobados); tasa BCV del día, reglamentos y panel "
            "administrativo para aceptar o rechazar pagos."
        ),
        "NestJS, MongoDB, Next.js, React, TypeScript, Tailwind CSS, JWT",
        "https://buildforge.work/",
    ),
    (
        "PokemonApp · cliente sobre la API oficial",
        (
            "Aplicación web que consume la API pública de Pokémon: exploración "
            "de especies/datos usando Angular en el cliente y backend en Python "
            "con PostgreSQL para persistencia y orquestación."
        ),
        "Angular, Python, PostgreSQL, API Pokémon (REST)",
        "https://pokemon.buildforge.work/home",
    ),
    (
        "Mobile Gastos (working)",
        (
            "Dominio centrado en gastos y deudas por perfil sobre periodos "
            "mensuales, categorías, conversión BCV y verificación asistida "
            "mediante OCR. Frontend mobile-first (Angular 20 en frontend/), "
            "API NestJS (backend/), PostgreSQL; servicio OCR/LLM en Python "
            "bajo `ocr/` invocado desde Nest por HTTP según especificación "
            "(repos independientes por carpeta; no es monorepo npm)."
        ),
        "Angular 20, NestJS, PostgreSQL, Python (OCR), Firebase",
        "https://mobilegastos.buildforge.work",
    ),
    (
        "Quiniela Mundial de fútbol 2026",
        (
            "Sistema web de quiniela para el Mundial (~100 usuarios): "
            "arquitectura cliente-servidor con API REST relacional PostgreSQL."
            " Módulos: usuarios (registro, login, perfil, JWT según especificación)"
            "; 64 partidos con cronograma y resultados; predicciones de marcador con"
            " bloqueo temporal; puntuación automática y tabla de ranking; chat grupal"
            " en tiempo real (p. ej. WebSockets según alcance)."
            " Frontend Next.js +"
            " React contra API FastAPI; job CRON 5–10 min para ingestar resultados"
            " desde API externa. Despliegue público pendiente por ahora."
        ),
        (
            "FastAPI, Python, Next.js, React, PostgreSQL, JWT, WebSockets, "
            "CRON externos"
        ),
        None,
    ),
)


async def ejecutar_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _buscar_filas_de_semilla(session, titulo: str, live_url: str | None):
    """Resuelve la fila de catálogo por URL cuando existe; si no, por título + sin URL."""
    if live_url is not None:
        result = await session.execute(
            select(Project).where(Project.live_url == live_url).limit(1)
        )
        return result.scalars().first()
    resultado_exacto = await session.execute(
        select(Project).where(Project.title == titulo, Project.live_url.is_(None)).limit(1)
    )
    fila_exacta = resultado_exacto.scalars().first()
    if fila_exacta is not None:
        return fila_exacta
    if "quiniela" in titulo.casefold():
        resuelto = await session.execute(
            select(Project)
            .where(Project.live_url.is_(None), Project.title.ilike("%quiniela%"))
            .order_by(Project.id)
            .limit(1)
        )
        return resuelto.scalars().first()
    return None


async def _deduplicar_quiniela_misma_live_url_none() -> None:
    """Si hay varias filas de quiniela sin deploy, conserva la de menor ``id``
    y suma ``visits`` de los duplicados antes de borrar los sobrantes."""
    async with AsyncSessionLocal() as session:
        resultado = await session.execute(
            select(Project)
            .where(Project.live_url.is_(None), Project.title.ilike("%quiniela%"))
            .order_by(Project.id)
        )
        filas = list(resultado.scalars().all())
        if len(filas) <= 1:
            return
        principal = filas[0]
        visitas_rest = sum((p.visits or 0) for p in filas[1:])
        if visitas_rest:
            principal.visits = (principal.visits or 0) + visitas_rest
        for extra in filas[1:]:
            await session.delete(extra)
        await session.commit()


async def semillar_catalogo_portfolio_si_falta() -> None:
    async with AsyncSessionLocal() as session:
        for titulo, descripcion, tech_stack, live_url in _SEMILLAS:
            proyecto = await _buscar_filas_de_semilla(session, titulo, live_url)
            if proyecto is not None:
                continue
            session.add(
                Project(
                    title=titulo,
                    description=descripcion,
                    tech_stack=tech_stack,
                    live_url=live_url,
                    repo_url=None,
                    image_url=None,
                    visits=0,
                )
            )
        await session.commit()


async def sincronizar_filas_catalogo_con_semilla() -> None:
    async with AsyncSessionLocal() as session:
        for titulo, descripcion, tech_stack, live_url_catalogo in _SEMILLAS:
            proyecto = await _buscar_filas_de_semilla(session, titulo, live_url_catalogo)
            if proyecto is None:
                continue
            if (
                proyecto.title == titulo
                and proyecto.description == descripcion
                and proyecto.tech_stack == tech_stack
                and (
                    live_url_catalogo is None
                    or proyecto.live_url == live_url_catalogo
                )
            ):
                continue
            proyecto.title = titulo
            proyecto.description = descripcion
            proyecto.tech_stack = tech_stack
            if live_url_catalogo is not None:
                proyecto.live_url = live_url_catalogo
        await session.commit()


async def inicializar_base_y_datos() -> None:
    await ejecutar_schema()
    await semillar_catalogo_portfolio_si_falta()
    await sincronizar_filas_catalogo_con_semilla()
    await _deduplicar_quiniela_misma_live_url_none()
