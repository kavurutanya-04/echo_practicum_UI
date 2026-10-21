# Echo Console

A local web interface for the Echo multi-agent prototype. Echo's agents are not modified: every
analysis runs `Agent_Echo/run_agent.py` as a subprocess, so the console gets exactly the same scope
checks, evidence rules and ZeroSugar verification as the terminal. Progress streams to the browser
from Echo's own JSONL execution log.

## Run it

Set up Echo first (see the root README: virtual environment, `import_data.py`). Then, on macOS/Linux:

```bash
./Echo_UI/start.sh
```

and open http://127.0.0.1:8765. The script installs FastAPI/Uvicorn into `Agent_Echo/.venv`,
installs and builds the frontend (Node 20+ required), and serves the API and the built UI on one
port, bound to localhost only. Use `./Echo_UI/start.sh --no-build` to skip rebuilding.

For frontend development with hot reload, run the backend and Vite separately:

```bash
cd Echo_UI/backend && ../../Agent_Echo/.venv/bin/python -m uvicorn app:app --port 8765 --reload
cd Echo_UI/frontend && npm run dev   # http://localhost:5173, proxies /api to 8765
```

## Features

- **Ask Echo** — manager scope and date window, offline demo or live models, connection picker
  (any `connections.json` profile with a key, or the per-agent split in `connections.local.json`),
  suggested questions.
- **Live agent pipeline** — the five agents light up as the execution log streams in, with a
  readable event timeline. Offline demos and finished runs can be replayed.
- **Cited answers** — `[SQL1]` / `[survey:CMT…]` citations open the exact query and result rows
  or the anonymous comment in a side panel. Findings show ZeroSugar's supported/withheld status.
- **Evidence, charts, review, sentiment** — SQL with copy and CSV export, interactive charts built
  from Lime's evidence-bound chart specs (plus Lime's own SVG/CSV files), the seven rubric ratings,
  and stacked sentiment percentages when Vanilla's classifier ran.
- **Runs** — searchable history, delete, and side-by-side comparison of two runs (for example, the
  same question on two models).
- **Team dashboard** — deterministic survey trends and a favorable-% heatmap from Echo's scoped
  data layer. No model calls.
- **Data** — the eleven tables with row counts and the schema dictionary.
- **Connections** — which profiles have keys (never the keys themselves) and an estimated
  free-tier usage meter per model, from Echo's run logs.

## Layout

```
Echo_UI/
  backend/app.py        FastAPI: /api/meta, /api/managers, /api/runs (+ SSE events), /api/quota, /api/data
  frontend/             React + TypeScript + Vite, Tailwind CSS v4, Recharts, lucide icons
  runs/                 one folder per console run: meta.json, artifact.json, console.txt, charts/ (git-ignored)
  start.sh              build and serve on http://127.0.0.1:8765
```

## Notes

- The manager picker is a demo scope, not authentication. Do not expose the server beyond localhost.
- Offline demos always run Echo's fixed scripted recognition review; a typed question is ignored.
- The usage meter counts only calls made through Echo, and Google can change free-tier limits.
- The repository's root `.gitignore` allow-lists top-level folders and does not list `Echo_UI/`.
  Changes to files already in Git are tracked normally, but a **new** file must be added with
  `git add -f <path>`. Never force-add `node_modules/`, `dist/` or `runs/` (see `Echo_UI/.gitignore`).
