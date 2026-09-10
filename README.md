# Portfolio API (FastAPI)

Backend del portafolio Buildforge: proyectos, GitHub cache, chat de cotización y analytics.

## Requisitos

- Python 3.14 (alineado con Dockerfile)
- PostgreSQL
- Redis (opcional, acelera cache GitHub)
- Ollama (opcional, mejora respuestas del chat)

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.local.example .env.local   # ajustar DATABASE_URL, etc.
uvicorn app.main:app --reload --port 8010
```

Tests y calidad:

```bash
pytest -q
bandit -r app -ll
pip-audit -r requirements-dev.txt
```

## Migraciones (Alembic)

Producción: aplicar antes del arranque o en el pipeline de deploy.

```bash
alembic upgrade head
# o
./scripts/migrate.sh
```

En dev/tests, `init_db` sigue usando `create_all` + semillas de catálogo.

## Admin — CRUD proyectos

Mutaciones `POST/PUT/DELETE /api/v1/projects` requieren header `X-Admin-Api-Key` (= env `ADMIN_API_KEY`).

```bash
export ADMIN_API_KEY=tu-clave
export API_BASE=http://127.0.0.1:8010/api/v1

./scripts/admin-projects.sh list
./scripts/admin-projects.sh create '{"title":"Demo","description":"Texto","status":"live"}'
./scripts/admin-projects.sh update 1 '{"is_featured":true}'
./scripts/admin-projects.sh delete 1
```

Verificación post-deploy:

```bash
API_BASE=https://tu-api.buildforge.work FRONT_URL=https://tu-front.buildforge.work ./scripts/verify-deploy.sh
```

## Checklist Coolify (producción)

| Variable / acción | Obligatorio | Notas |
|-------------------|-------------|-------|
| `DATABASE_URL` | Sí | PostgreSQL interno |
| `ADMIN_API_KEY` | Sí | Secreto largo; header admin |
| `FORWARDED_ALLOW_IPS` | Sí | Redes del proxy; nunca `*` |
| `BACKEND_CORS_ORIGINS` | Sí | URL del front sin barra final |
| `REDIS_URL` o `REDIS_*` | Recomendado | Cache GitHub |
| `GITHUB_TOKEN` | Recomendado | Rate limit API |
| `OLLAMA_BASE_URL` | Opcional | Chat con LLM |
| `alembic upgrade head` | Primera vez | Antes o al deploy |
| Build Pack | Dockerfile | Puerto `8010` expuesto |

Ver comentarios en [`.env.local.example`](.env.local.example).

## Estructura

```
app/
  api/v1/endpoints/   # projects, github, chat, analytics
  core/               # config, dependencies (DI)
  services/           # chat, github, cache, ollama
  security/           # admin auth, rate limit
alembic/versions/     # migraciones
scripts/              # migrate, admin-projects
tests/
```
