# Mobile Gastos — MVP principal del portfolio

## Rol en el sitio

- **Proyecto destacado:** único con `is_featured: true` y `sort_order: 0`.
- **Estado catálogo:** `mvp_active` (badge "MVP ACTIVO", CTA "PROBAR DEMO WEB").
- **Banner home:** sección `#producto-destacado` (`FeaturedProductBanner`); no duplicar otro featured.
- **Demo:** https://mobilegastos.buildforge.work
- **Staging:** https://developgastos.buildforge.work

## Qué es (una frase)

App **mobile-first** de finanzas personales y deudas por **perfil** (familia/grupo/comercio), con presupuesto mensual o por **día de corte**, categorías, **tasa BCV**, OCR de comprobantes y módulo de **inventario** para comercios.

## Stack real (no inventar en copy público)

| Capa | Tecnología |
|------|------------|
| Frontend | Angular 20 (SPA, PWA-oriented) |
| API | NestJS + Prisma |
| BD | PostgreSQL |
| Auth | Email/contraseña + Firebase (intercambio JWT en backend) |
| OCR | Tesseract.js + glm-ocr vía Ollama en Nest; feedback usuario → `OcrCorrectionSample` |
| Deploy | Coolify → Cloudflare (BuildForge) |

Repositorio de producto: carpeta `gastos/` (frontend, backend, obsidian-vault). **No es monorepo npm.**

## Funcionalidades implementadas (MVP actual)

1. **Cuenta:** registro/login, setup de contraseña, reset, desbloqueo por OTP.
2. **Presupuesto:** ingreso mensual, moneda USD/BS, arrastre de superávit, renovación mensual (zona Caracas).
3. **FEAT-001:** ciclo con día de corte configurable (1–28).
4. **Perfiles:** familiar / grupal / comercio; miembros para auditar quién pagó.
5. **Gastos:** checklist pendiente/pagado, categorías, gráficos, historial por mes, comprobante en imagen.
6. **BCV:** cotización oficial cacheada; conversión al registrar en bolívares.
7. **OCR:** parseo de factura desde imagen; confirmación rápida o formulario; muestras de corrección para mejorar precisión.
8. **FEAT-002–004 (comercio):** inventario, sucursales, transferencias, precios opcionales, colaboradores invitados.

## Mensajes de marketing (usar tal cual o acortar)

- **Banner corto:** Finanzas personales y familiares con demo web hoy y app móvil en desarrollo. Presupuestos por perfil (familiar/grupal/comercio), día de corte configurable, OCR de comprobantes y tasa BCV — camino a beta y tiendas.
- **Subtítulo misión:** Demo web disponible · App móvil en desarrollo · Camino al mercado
- **Early adopter:** asunto `Mobile Gastos — early adopter` (ya en `mission-presentation.ts`)

## Reglas al editar el portfolio

- No quitar `is_featured` de Mobile Gastos sin reemplazar otro proyecto explícitamente.
- Actualizar **semilla** en `backend/app/db/init_db.py` y textos del banner si cambia el pitch o la URL demo.
- `tech_stack` en API: chips separados por coma; incluir `MVP`, `Web live`, `Mobile WIP` para estilos en `MissionCard`.
- Repo privado: dejar `repo_url` null o poner enlace GitHub solo si es público.

## Fuente de verdad técnica (repo Gastos)

- `obsidian-vault/02-Proyecto/Contexto-agents.md`
- `obsidian-vault/02-Proyecto/Vision.md`
- Specs: `obsidian-vault/04-Especificaciones/features/FEAT-*.md`

## Semilla actual en `init_db.py`

```python
SemillaProyecto(
    titulo="Mobile Gastos · MVP en evolución",
    descripcion=(
        "MVP de finanzas personales y familiares: gastos y deudas por perfil "
        "(familiar, grupal o comercio), presupuesto con día de corte configurable, "
        "categorías con gráficos, tasa BCV (Bs/USD) y captura de comprobantes con OCR "
        "(Tesseract + visión local vía Ollama). Para comercios: inventario multi-sucursal, "
        "transferencias y colaboradores invitados. Demo web en producción; "
        "experiencia móvil nativa/PWA en evolución sobre Angular 20 y API NestJS "
        "(PostgreSQL, Prisma, despliegue Coolify)."
    ),
    tech_stack=(
        "MVP, Web live, Mobile WIP, Angular 20, NestJS, PostgreSQL, Prisma, "
        "Ollama (OCR), Firebase Auth, Docker, Coolify"
    ),
    live_url="https://mobilegastos.buildforge.work",
    status=ProjectStatus.MVP_ACTIVE.value,
    is_featured=True,
    sort_order=0,
)
```
