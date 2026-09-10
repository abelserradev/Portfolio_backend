#!/usr/bin/env bash
# CRUD de proyectos vía API admin. Requiere ADMIN_API_KEY en el backend desplegado.
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8010/api/v1}"
ADMIN_KEY="${ADMIN_API_KEY:?Exporta ADMIN_API_KEY}"

cmd="${1:-help}"

case "$cmd" in
  list)
    curl -sS "${API_BASE}/projects/" | jq .
    ;;
  create)
    payload="${2:?JSON del proyecto, ej. {\"title\":\"Demo\",\"description\":\"...\"}}"
    curl -sS -X POST "${API_BASE}/projects/" \
      -H "Content-Type: application/json" \
      -H "X-Admin-Api-Key: ${ADMIN_KEY}" \
      -d "$payload" | jq .
    ;;
  update)
    id="${2:?project_id}"
    payload="${3:?JSON parcial}"
    curl -sS -X PUT "${API_BASE}/projects/${id}" \
      -H "Content-Type: application/json" \
      -H "X-Admin-Api-Key: ${ADMIN_KEY}" \
      -d "$payload" | jq .
    ;;
  delete)
    id="${2:?project_id}"
    curl -sS -X DELETE "${API_BASE}/projects/${id}" \
      -H "X-Admin-Api-Key: ${ADMIN_KEY}" -w "\nHTTP %{http_code}\n"
    ;;
  *)
    cat <<'EOF'
Uso:
  ADMIN_API_KEY=... ./scripts/admin-projects.sh list
  ADMIN_API_KEY=... ./scripts/admin-projects.sh create '{"title":"X","description":"Y"}'
  ADMIN_API_KEY=... ./scripts/admin-projects.sh update 1 '{"is_featured":true}'
  ADMIN_API_KEY=... ./scripts/admin-projects.sh delete 1

Variables: API_BASE (default http://127.0.0.1:8010/api/v1)
EOF
    ;;
esac
