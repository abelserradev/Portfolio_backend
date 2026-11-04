#!/usr/bin/env bash
# Post-deploy: valida health y variables críticas documentadas en README (issues #1, #2, #22).
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8010}"
FRONT_URL="${FRONT_URL:-http://127.0.0.1:3000}"

echo "== API root =="
curl -sf "${API_BASE}/" | head -c 200
echo

echo "== Chat health =="
curl -sf "${API_BASE}/api/v1/chat/health"
echo

echo "== Projects públicos =="
curl -sf "${API_BASE}/api/v1/projects/" | head -c 300
echo

echo "== Front home =="
curl -sfI "${FRONT_URL}/" | head -5

cat <<'EOF'

Checklist manual Coolify (no automatizable desde aquí):
  - ADMIN_API_KEY configurada
  - FORWARDED_ALLOW_IPS = redes del proxy (nunca *)
  - BACKEND_CORS_ORIGINS incluye URL del front
  - alembic upgrade head en primer deploy
EOF
