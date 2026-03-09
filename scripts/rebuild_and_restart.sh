#!/usr/bin/env bash
set -euo pipefail

COMPOSE="docker compose"
MIGRATION_COMMAND="${MIGRATION_COMMAND:-python3.13 -m aerich upgrade}"

mkdir -p logs

echo "[1/5] Stopping current containers..."
$COMPOSE down

echo "[2/5] Rebuilding images..."
$COMPOSE build

echo "[3/5] Starting postgres and redis..."
$COMPOSE up -d postgres redis

echo "[4/5] Waiting for postgres healthcheck..."
until [ "$($COMPOSE ps --format json postgres 2>/dev/null | python3.13 - <<'PY'
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        data = data[0] if data else {}
    print(data.get('Health', ''))
except Exception:
    print('')
PY
)" = "healthy" ]; do
  sleep 2
  echo "Postgres is not healthy yet..."
done

echo "[5/5] Applying migrations..."
$COMPOSE run --rm bot sh -lc "$MIGRATION_COMMAND"

echo "Starting all containers..."
$COMPOSE up -d

echo "Done."
