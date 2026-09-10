#!/usr/bin/env bash
# Aplicar migraciones Alembic (prod: ejecutar antes o al arrancar el contenedor).
set -euo pipefail
cd "$(dirname "$0")/.."
alembic upgrade head
