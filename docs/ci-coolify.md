# CI and Coolify deploy

## Local hooks

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

Pre-commit: gitleaks + `compileall` on staged Python.  
Pre-push: `pytest -q` (tests use in-memory SQLite via `tests/conftest.py`).

## GitHub Actions

- **CI** — lint/deps/audit/compileall/pytest on `main`, `master`, `develop`.
- **Deploy Coolify** — runs after a successful CI on `main`/`develop`, or via `workflow_dispatch`.

### Repository secrets

| Secret | Value |
|--------|--------|
| `COOLIFY_WEBHOOK_BACKEND` | Full **Deploy Webhook (auth required)** URL from the Coolify application (Webhooks panel) |
| `COOLIFY_TOKEN` | Coolify API token with **deploy** permission (`Authorization: Bearer`) |

Do not commit the webhook URL or token. Coolify deploy webhooks require Bearer auth; the workflow fails if either secret is missing.

## Avoid double deploys

In Coolify → Application → Advanced → Deployment, set **Manual deployments only** (disable auto-deploy on git push) when GitHub Actions already triggers the Deploy webhook after CI.
