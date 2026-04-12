#!/usr/bin/env bash
# Сборка и запуск стека через Docker Compose, затем миграции Aerich внутри уже
# запущенного контейнера сервиса `bot`.
#
# Предпосылки: в docker-compose.yml должен быть включён сервис `bot`; для БД —
# корректный `.env` (PG_* и т.д.).
# Переопределить команду миграций: MIGRATION_COMMAND='python -m aerich upgrade' ./scripts/build_up_migrate.sh

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose"
MIGRATION_COMMAND="${MIGRATION_COMMAND:-python -m aerich upgrade}"

echo "[1/4] Building images..."
$COMPOSE build

echo "[2/4] Starting containers..."
$COMPOSE up -d

echo "[3/4] Waiting for postgres healthcheck..."
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

echo "[4/4] Applying migrations in bot container..."
$COMPOSE exec -T bot sh -lc "$MIGRATION_COMMAND"

echo "Done."
