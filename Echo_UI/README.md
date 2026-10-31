# Echo Console

Current runtime, 2026-10-27: review-v5 uses concise assertion descriptions instead of
literal answer reconstruction. Technical Evidence checks can include assigned assertion
IDs; legacy fields remain readable. New artifacts link private full captures/checkpoints;
the manager projection excludes these details. Phase-only retry is currently a CLI
operation, documented in [capture/resumption](../Agent_Echo/RESUME_AND_CAPTURE.md), not a
new manager workflow. No build, browser test or provider call validated this update.

Current support review, 2026-10-27: review-v4 findings include individual assertion
assessments; this field is optional when reading historical artifacts. The technical
Answer view exposes Evidence checks with claim, sources, judgment and reason. The
manager projection is unchanged. The production build passed; browser interaction and
a new live workflow remain unverified. See the
[runtime contract](../Agent_Echo/WORKFLOW_RELIABILITY.md#assertion-level-support-review-review-v4-2026-10-27).

Current review contract, 2026-10-27: [review-v3 correction judgments](../Agent_Echo/WORKFLOW_RELIABILITY.md#explicit-correction-judgments-after-run-twenty-one-2026-10-27) retain canonical correction states, ratings and reviewed-source identities while code derives states from explicit model judgments. Historical review-v2 and answer replay remain supported; five roles and the manager UI flow are unchanged. Runtime checks and their limits are recorded in the linked testing guide; no UI build or complete workflow validation is claimed here.

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
- **Your team panel (manager view)** — one slide-out panel with four tabs: *What changed* (latest survey
  quarter compared with the one before), *Goals* (measures saved with "Track next quarter", with their latest
  value), *Gaps* (praised cross-team work with no manager-recognition record; "Mark as thanked" is stored only
  in the browser) and *Team pulse*. Served by `/api/managers/{id}/updates`, which runs scoped read-only SQL
  without model calls and never reads survey comment text.
- **Business-oriented briefs** — each answer adds a "Why it matters" box (risk to engagement,
  retention, delivery or capacity, stated without invented numbers or causal claims), business-framed next steps, and
  metrics to watch that also appear in the Your team panel. The same text goes into the Power BI description.
- **Open a chart in Power BI** — clicking any answer chart (manager view or console) asks first, then downloads a
  zipped Power BI Project (PBIP: PBIR report + TMDL model, generally available in Power BI Desktop since September
  2026) from `/api/runs/{id}/charts/{source}/powerbi.zip`. Extract it and open the `.pbip` file: one page with the
  chart in Echo's pastel theme, the question, findings, limitations, a data table and a privacy note. The plotted
  columns are embedded as a DAX `DATATABLE`, so it opens offline with no data source; nothing else is exported. The
  plain CSV is also available at `/api/runs/{id}/charts/{source}/data.csv`. Generated JSON files are validated
  against Microsoft's published PBIR schemas; opening in Power BI Desktop itself has not been tested here.
- **Open a chart in Tableau or Excel** — the same dialog has an "Open in" dropdown (Power BI, Tableau, Excel; the
  last choice is remembered). Tableau: `/api/runs/{id}/charts/{source}/tableau.twbx`, a packaged workbook (TWB 26.1
  with the chart's CSV inside) that opens on the chart, with the description in the worksheet caption; the XML is
  validated against Tableau's published TWB 2026.1 schema, so Tableau 2026.1 or newer is needed. Excel:
  `/api/runs/{id}/charts/{source}/excel.xlsx` (needs `openpyxl`, in `backend/requirements.txt`): a native Excel chart
  in the pastel palette with the description on the first sheet and the numbers on a Numbers sheet. All three share
  one description (question, findings, why it matters, what to do first, limitations). Neither file has been opened
  in Tableau or Excel here; the Excel file was checked by rendering it in LibreOffice.
- **Layout options** — the suggested questions can be hidden down to the first three ("Show N more" brings the rest
  back, however many there are), and the agents box can be minimized to a one-line strip that still shows which agent
  is working. Both choices are remembered in the browser.
- **Investigations and Present** — a question asked while an investigation is open is added to it as a follow-up;
  **New investigation** (sidebar or the investigation bar) starts a fresh one. Earlier results fold up under the
  latest. **Present** opens `/present/{investigation}` in a new tab: a designed 16:9 deck (cover, agenda, per
  question a findings + chart slide and a "what it means / what to do" slide, actions for the quarter, how it was
  checked) with arrow-key navigation and full screen. **Save as PDF** prints one slide per page; **Download
  PowerPoint** calls `/api/presentation.pptx?manager_id=…&runs=…` (needs `python-pptx`) for an editable deck with
  native charts. Slides use only the results' own manager projections; the endpoint refuses runs of another manager.
  Checked here by rendering the .pptx in LibreOffice and the PDF in headless Chromium; not opened in PowerPoint.
- **Team dashboard** — deterministic survey trends and a favorable-% heatmap from Echo's scoped
  data layer. No model calls.
- **Data** — the eleven tables with row counts and the schema dictionary.
- **Connections** — which profiles have keys (never the keys themselves) and an estimated
  free-tier usage meter per model, from Echo's run logs.

## Layout

```
Echo_UI/
  backend/app.py        FastAPI: /api/meta, /api/managers (+ /updates, /pulse), /api/runs (+ SSE events, chart CSV and Power BI project), /api/quota, /api/data
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
