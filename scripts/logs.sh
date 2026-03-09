#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-bot}"
exec docker compose logs -f "$SERVICE"
