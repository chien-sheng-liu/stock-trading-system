#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Starting backend (http://127.0.0.1:5000)"
pushd "$ROOT_DIR/backend" >/dev/null
if ! python -c "import uvicorn" >/dev/null 2>&1; then
  echo "[warn] 'uvicorn' not found. Install deps: pip install -r requirements.txt" >&2
fi
python -m uvicorn main:app --reload --host 127.0.0.1 --port 5000 &
BACKEND_PID=$!
popd >/dev/null

echo "==> Starting frontend (http://localhost:3000)"
pushd "$ROOT_DIR/frontend" >/dev/null
if [ ! -d node_modules ]; then
  echo "[note] 'node_modules' missing. Run: npm install" >&2
fi
npm run dev &
FRONTEND_PID=$!
popd >/dev/null

echo "==> Backend PID: $BACKEND_PID"
echo "==> Frontend PID: $FRONTEND_PID"
echo "==> Both running. Press Ctrl+C to stop."

cleanup() {
  echo "\n==> Stopping services..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

wait

