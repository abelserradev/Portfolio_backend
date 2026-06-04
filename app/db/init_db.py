"""
Arranque de esquema y proyectos ejemplo del portfolio sin migraciones Alembic.

Cada proyecto del catálogo se inserta si aún no existe: con ``live_url`` se busca
por URL; si es ``None`` (despliegue pendiente), se usa el título exacto más
``live_url IS NULL``. Para la quiniela, si el título del catálogo cambió respecto
a filas antiguas, se reutiliza la primera fila que coincida por patrón (evita
duplicados al renombrar). Tras sincronizar, se eliminan filas duplicadas de
quiniela conservando el ``id`` más bajo.

Las filas del catálogo se reconcilian (título, descripción, tech_stack,
``live_url``, ``status``, ``is_featured``, ``sort_order``) al arrancar.
"""

from dataclasses import dataclass

from sqlalchemy import select, text

from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models.project import Project
from app.models.project_status import ProjectStatus


@dataclass(frozen=True)
class SemillaProyecto:
    titulo: str
    descripcion: str
    tech_stack: str
    live_url: str | None
    status: str = ProjectStatus.LIVE.value
    is_featured: bool = False
    sort_order: int = 100


_SEMILLAS: tuple[SemillaProyecto, ...] = (
    SemillaProyecto(
        titulo="Mobile Gastos · MVP en evolución",
        descripcion=(
            "MVP de finanzas personales: control de gastos y deudas por perfil, "
            "periodos mensuales, categorías, conversión BCV y comprobantes con OCR. "
            "Demo web disponible hoy; aplicación móvil en desarrollo activo "
            "sobre Angular 20 y API NestJS (PostgreSQL, servicio OCR en Python). "
            "Producto orientado a salir al mercado (beta / tiendas en preparación)."
        ),
        tech_stack=(
            "MVP, Web live, Mobile WIP, Angular 20, NestJS, PostgreSQL, "
            "Python (OCR), Firebase"
        ),
        live_url="https://mobilegastos.buildforge.work",
        status=ProjectStatus.MVP_ACTIVE.value,
        is_featured=True,
        sort_order=0,
    ),
    SemillaProyecto(
        titulo="SambilStore · e-commerce moderno",
        descripcion=(
            "Aplicación de e-commerce completa construida como prueba técnica freelance. "
            "Implementa infinite scroll, búsqueda en tiempo real, carrito de compras con persistencia "
            "en localStorage, y filtrado por categorías. Diseño responsive mobile-first con "
            "optimizaciones de performance avanzadas incluyendo lazy loading y Core Web Vitals."
        ),
        tech_stack="Next.js 15, React 19, TypeScript 5, Tailwind CSS v4, FakeStore API, Heroicons",
        live_url="https://sambilstore.vercel.app/",
        sort_order=10,
    ),
    SemillaProyecto(
        titulo="Condominio BuildForge · recibos y cobros",
        descripcion=(
            "Portal para administración del condominio: la administración emite "
            "y gestiona recibos y cobros; los propietarios consultan deudas, "
            "reportan pagos adjuntando comprobantes y visualizan el estado "
            "(pendientes, aprobados); tasa BCV del día, reglamentos y panel "
            "administrativo para aceptar o rechazar pagos."
        ),
        tech_stack="NestJS, MongoDB, Next.js, React, TypeScript, Tailwind CSS, JWT",
        live_url="https://buildforge.work/",
        sort_order=20,
    ),
    SemillaProyecto(
        titulo="PokemonApp · cliente sobre la API oficial",
        descripcion=(
            "Aplicación web que consume la API pública de Pokémon: exploración "
            "de especies/datos usando Angular en el cliente y backend en Python "
            "con PostgreSQL para persistencia y orquestación."
        ),
        tech_stack="Angular, Python, PostgreSQL, API Pokémon (REST)",
        live_url="https://pokemon.buildforge.work/home",
        sort_order=30,
    ),
    SemillaProyecto(
        titulo="Quiniela Mundial de fútbol 2026",
        descripcion=(
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
        tech_stack=(
            "FastAPI, Python, Next.js, React, PostgreSQL, JWT, WebSockets, "
            "CRON externos"
        ),
        live_url=None,
        status=ProjectStatus.IN_DEVELOPMENT.value,
        sort_order=40,
    ),
)


async def ejecutar_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _asegurar_columnas_catalogo() -> None:
    """PostgreSQL: tablas ya creadas no ganan columnas con create_all."""
    sentencias = (
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(32) "
        f"NOT NULL DEFAULT '{ProjectStatus.LIVE.value}'",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_featured BOOLEAN "
        "NOT NULL DEFAULT false",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS sort_order INTEGER "
        "NOT NULL DEFAULT 100",
    )
    async with engine.begin() as conn:
        for sql in sentencias:
            await conn.execute(text(sql))


async def _buscar_filas_de_semilla(session, semilla: SemillaProyecto):
    """Resuelve la fila de catálogo por URL cuando existe; si no, por título + sin URL."""
    live_url = semilla.live_url
    titulo = semilla.titulo
    if live_url is not None:
        result = await session.execute(
            select(Project).where(Project.live_url == live_url).limit(1)
        )
        fila = result.scalars().first()
        if fila is not None:
            return fila
        if "mobilegastos" in live_url.casefold():
            legado = await session.execute(
                select(Project)
                .where(Project.live_url.ilike("%mobilegastos%"))
                .order_by(Project.id)
                .limit(1)
            )
            return legado.scalars().first()
        return None
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


def _aplicar_semilla_en_fila(proyecto: Project, semilla: SemillaProyecto) -> None:
    proyecto.title = semilla.titulo
    proyecto.description = semilla.descripcion
    proyecto.tech_stack = semilla.tech_stack
    proyecto.status = semilla.status
    proyecto.is_featured = semilla.is_featured
    proyecto.sort_order = semilla.sort_order
    if semilla.live_url is not None:
        proyecto.live_url = semilla.live_url


def _fila_desactualizada(proyecto: Project, semilla: SemillaProyecto) -> bool:
    if proyecto.title != semilla.titulo:
        return True
    if proyecto.description != semilla.descripcion:
        return True
    if proyecto.tech_stack != semilla.tech_stack:
        return True
    if getattr(proyecto, "status", None) != semilla.status:
        return True
    if bool(getattr(proyecto, "is_featured", False)) != semilla.is_featured:
        return True
    if getattr(proyecto, "sort_order", 100) != semilla.sort_order:
        return True
    if semilla.live_url is not None and proyecto.live_url != semilla.live_url:
        return True
    return False


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
        for semilla in _SEMILLAS:
            proyecto = await _buscar_filas_de_semilla(session, semilla)
            if proyecto is not None:
                continue
            session.add(
                Project(
                    title=semilla.titulo,
                    description=semilla.descripcion,
                    tech_stack=semilla.tech_stack,
                    live_url=semilla.live_url,
                    status=semilla.status,
                    is_featured=semilla.is_featured,
                    sort_order=semilla.sort_order,
                    repo_url=None,
                    image_url=None,
                    visits=0,
                )
            )
        await session.commit()


async def sincronizar_filas_catalogo_con_semilla() -> None:
    async with AsyncSessionLocal() as session:
        for semilla in _SEMILLAS:
            proyecto = await _buscar_filas_de_semilla(session, semilla)
            if proyecto is None:
                continue
            if not _fila_desactualizada(proyecto, semilla):
                continue
            _aplicar_semilla_en_fila(proyecto, semilla)
        await session.commit()


async def inicializar_base_y_datos() -> None:
    await ejecutar_schema()
    await _asegurar_columnas_catalogo()
    await semillar_catalogo_portfolio_si_falta()
    await sincronizar_filas_catalogo_con_semilla()
    await _deduplicar_quiniela_misma_live_url_none()
