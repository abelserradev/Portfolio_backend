# CI and Coolify deploy

## Local hooks

`pre-commit` is not listed in `requirements-dev.txt` (keeps the app/dev test deps lean). Install the tool once in your venv, then register both hook stages:

```bash
# From Portfolio_backend/, with venv active and deps installed:
pip install -r requirements-dev.txt
pip install pre-commit

# On Windows, Scripts/ is often missing from PATH — prefer the module form:
python -m pre_commit install                    # pre-commit stage (commit)
python -m pre_commit install --hook-type pre-push
# Equivalent if `pre-commit` is on PATH: pre-commit install && pre-commit install --hook-type pre-push
```

### What runs

| Stage | Hooks |
|-------|--------|
| **pre-commit** | `gitleaks`; hygiene (`trailing-whitespace`, `check-yaml`, `check-ast`, …); `hadolint-docker` on root `Dockerfile`; Ruff lint+format; `bandit` on `app/`; `pip-audit` when `requirements*.txt` change |
| **pre-push** | `pytest -q` (in-memory SQLite via `tests/conftest.py`; no Postgres required) |

`hadolint-docker` needs a working Docker daemon. First Ruff run may rewrite files (`--fix` + format) — review the diff before committing.

### Manual runs (same gates as git)

```bash
# All pre-commit-stage hooks on every file
pre-commit run --all-files

# Pre-push-stage hooks (pytest) without pushing
pre-commit run --hook-stage pre-push --all-files
```

Skip once only if you must: `SKIP=gitleaks git commit …` or `git push --no-verify` (prefer fixing the failure).

## GitHub Actions

- **CI** — lint/deps/audit/compileall/pytest on `main`, `master`, `develop`.
- **Deploy Coolify** — runs after a successful CI on `main`/`develop`, or via `workflow_dispatch`, on a **self-hosted** runner (`portfolio-coolify`) on the Coolify host.

### Self-hosted runner

Public `coolify.buildforge.work` returns Cloudflare 403 to GitHub-hosted runners. Deploy jobs therefore use:

- `runs-on: [self-hosted, linux, portfolio-coolify]`
- Local API: `http://127.0.0.1:8000/api/v1/deploy?uuid=<app>&force=false`

Runners live on the server under `~/actions-runner-portfolio-backend` (started via `~/bin/start-portfolio-runners.sh`, also `@reboot` crontab). `sudo` is required only if you later convert them to systemd services with `svc.sh`.

### Repository secrets

| Secret | Value |
|--------|--------|
| `COOLIFY_WEBHOOK_BACKEND` | `http://127.0.0.1:8000/api/v1/deploy?uuid=<backend-uuid>&force=false` |
| `COOLIFY_TOKEN` | Coolify API token with **deploy** permission (`Authorization: Bearer`) |

Do not commit the URL or token. Trailing CR/LF from pasted secrets are trimmed in the job (curl exit 43).

## Avoid double deploys

Keep Coolify **Manual deployments only** / auto-deploy off when GitHub Actions triggers deploy after CI.
