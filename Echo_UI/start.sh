#!/usr/bin/env bash
# Build the frontend (if needed) and serve the whole console at http://127.0.0.1:8765
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$HERE/../Agent_Echo/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "Set up Echo first: cd Agent_Echo && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi
"$PYTHON" -m pip install -q -r "$HERE/backend/requirements.txt"
if [ ! -d "$HERE/frontend/node_modules" ]; then (cd "$HERE/frontend" && npm install); fi
if [ "${1:-}" != "--no-build" ]; then (cd "$HERE/frontend" && npm run build); fi
echo "Echo Console: http://127.0.0.1:8765"
cd "$HERE/backend" && exec "$PYTHON" -m uvicorn app:app --host 127.0.0.1 --port 8765
