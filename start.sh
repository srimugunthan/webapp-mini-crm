#!/usr/bin/env bash
# Start the backend (FastAPI on :8000) and the frontend dev server (Vite on :5173).
# Open http://localhost:5173 for the UI with live reload; the API proxy points at the backend.
# Press Ctrl+C to stop both.
#
#   ./start.sh          dev mode: backend --reload + Vite dev server
#   ./start.sh --built  build the UI once and serve everything from the backend on :8000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

command -v uv >/dev/null 2>&1 || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Node/npm is required."; exit 1; }

mkdir -p "$ROOT/db" "$ROOT/data"
export DB_PATH="${DB_PATH:-$ROOT/db/crm.sqlite}"
export DATA_DIR="${DATA_DIR:-$ROOT/data}"

echo "==> Installing dependencies (skipped when up to date)"
(cd backend && uv sync --quiet)
if [ ! -d frontend/node_modules ]; then (cd frontend && npm install); fi

if [ "${1:-}" = "--built" ]; then
  echo "==> Building the UI"
  (cd frontend && npm run build)
  echo "==> App running at http://127.0.0.1:8000  (Ctrl+C to stop)"
  cd backend
  STATIC_DIR="$ROOT/frontend/dist" exec uv run uvicorn app.asgi:app --host 127.0.0.1 --port 8000
fi

pids=()
cleanup() {
  trap - INT TERM EXIT
  echo; echo "==> Stopping..."
  for p in "${pids[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> Starting backend on http://127.0.0.1:8000"
(cd backend && STATIC_DIR="" exec uv run uvicorn app.asgi:app --host 127.0.0.1 --port 8000 --reload) &
pids+=($!)

echo "==> Starting frontend on http://localhost:5173"
(cd frontend && exec npm run dev -- --host 127.0.0.1) &
pids+=($!)

echo "==> Open http://localhost:5173   (Ctrl+C to stop both)"
wait
