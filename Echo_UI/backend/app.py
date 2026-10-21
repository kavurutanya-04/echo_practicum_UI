"""Echo UI backend: a thin local API around the existing Echo command-line workflow.

Echo itself is not modified. Each analysis runs `Agent_Echo/run_agent.py` as a subprocess, so the
UI gets exactly the same scope checks, evidence rules and verification as the terminal. Progress is
streamed to the browser from Echo's own JSONL execution log.
"""

import asyncio
import csv
import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
ECHO = ROOT / "Agent_Echo"
DATABASE = ECHO / "data" / "echo.db"
LOGS = ECHO / "reports" / "logs"
DICTIONARY = ROOT / "files_update" / "QA_data_dictionary.csv"
RUNS = Path(__file__).resolve().parents[1] / "runs"
FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "dist"
PYTHON = ECHO / ".venv" / "bin" / "python"
LOCAL_CONNECTIONS = ECHO / "connections.local.json"
SCOPE_MIN, SCOPE_MAX = "2024-10-01", "2026-09-30"
FREE_TIER_DAILY_LIMIT = 20

sys.path.insert(0, str(ECHO))
from agents.data_access import AccessScope, ScopedData  # noqa: E402

RUNS.mkdir(parents=True, exist_ok=True)
PROCESSES: dict[str, subprocess.Popen] = {}

app = FastAPI(title="Echo UI", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

SUGGESTED_QUESTIONS = [
    "What do this quarter's recognition metrics and comments suggest?",
    "Show Recognition over eight quarters by team.",
    "How many cross-team contributions lack a recorded manager-recognition note?",
    "Which weeks exceed available project hours?",
    "What percentage of Recognition comments is negative this quarter?",
    "What explains the recent priority changes?",
]


# ---------- helpers ----------

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def write_json(path, value):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def private_settings():
    """Read the private .env without ever returning secret values to the browser."""
    try:
        from dotenv import dotenv_values
        return dotenv_values(ECHO / ".env", encoding="utf-8-sig", interpolate=False)
    except Exception:
        return {}


def database():
    if not DATABASE.is_file():
        raise HTTPException(503, "Echo's database is missing. Run Agent_Echo/import_data.py first.")
    connection = sqlite3.connect(DATABASE.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def run_dir(run_id):
    if not run_id.replace("_", "").isalnum():
        raise HTTPException(404, "Unknown run.")
    path = RUNS / run_id
    if not (path / "meta.json").is_file():
        raise HTTPException(404, "Unknown run.")
    return path


def connection_configs():
    configs = {"default": read_json(ECHO / "connections.json", {})}
    if LOCAL_CONNECTIONS.is_file():
        configs["local"] = read_json(LOCAL_CONNECTIONS, {})
    return configs


def profile_model(profile, settings):
    variable = profile.get("model_env", "")
    return os.getenv(variable) or settings.get(variable) or profile.get("model", "")


# ---------- metadata ----------

@app.get("/api/meta")
def meta():
    settings = private_settings()
    configs = connection_configs()
    profiles = []
    for name, profile in configs["default"].get("profiles", {}).items():
        if profile.get("api") == "embeddings":
            continue
        key = profile.get("key_env", "")
        profiles.append({
            "name": name, "provider": profile.get("provider"), "model": profile_model(profile, settings),
            "description": profile.get("description", ""),
            "key_configured": bool(os.getenv(key) or settings.get(key)),
        })
    split = None
    if "local" in configs:
        local = configs["local"]
        split = {agent: profile_model(local["profiles"][name], settings)
                 for agent, name in local.get("agents", {}).items() if name in local.get("profiles", {})}
    return {"profiles": profiles, "default_profile": configs["default"].get("default_profile"),
            "local_split": split, "scope_min": SCOPE_MIN, "scope_max": SCOPE_MAX,
            "suggested_questions": SUGGESTED_QUESTIONS}


@app.get("/api/managers")
def managers():
    with database() as db:
        rows = db.execute("""SELECT Manager_ID, Manager_Name, Primary_Department, Primary_Team, Pilot_Assigned_Employees
                             FROM HR_managers ORDER BY Manager_ID""").fetchall()
    return [dict(row) for row in rows]


@app.get("/api/manager/{code}")
def manager_lookup(code: str):
    """Resolve a typed manager code (e.g. "m14") without listing every manager."""
    with database() as db:
        row = db.execute("""SELECT Manager_ID, Manager_Name, Primary_Department, Primary_Team, Pilot_Assigned_Employees
                            FROM HR_managers WHERE UPPER(Manager_ID) = UPPER(?)""", (code.strip(),)).fetchone()
    if row is None:
        raise HTTPException(404, "No manager has that code.")
    return dict(row)


@app.get("/api/managers/{manager_id}/overview")
def manager_overview(manager_id: str, start: str = SCOPE_MIN, end: str = SCOPE_MAX):
    """Deterministic team dashboard from Echo's own scoped access layer (no model calls)."""
    try:
        scope = AccessScope(manager_id, start, end)
        data = ScopedData(DATABASE, scope)
    except ValueError as error:
        raise HTTPException(400, str(error))
    try:
        columns, rows = data.survey_rows()
        survey = [dict(zip(columns, row)) for row in rows]
        _, employees = data.employee_rows("HR_employees", "Employee_ID", fields="Employee_ID")
        _, contributions = data.employee_rows("OP_contributions", "Employee_ID", "Contribution_Date", "Contribution_ID")
        _, comments = data.survey_rows(comments=True)
        return {"manager": data.manager, "teams": data.teams, "scope": scope.__dict__,
                "headcount": len(employees), "contributions": len(contributions), "comments": len(comments),
                "survey": [{key: row[key] for key in ("Survey_Date", "Team", "Dimension", "Responses", "Eligible_Employees",
                                                       "Mean_Score", "Favorable_Percent", "eNPS_Score")} for row in survey]}
    finally:
        data.close()


@app.get("/api/data/tables")
def tables():
    dictionary = {}
    try:
        with DICTIONARY.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                dictionary.setdefault(row["File"].removesuffix(".csv"), []).append(row)
    except OSError:
        pass
    with database() as db:
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts = {name: db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in names}
    return [{"name": name, "rows": counts[name], "columns": dictionary.get(name, [])} for name in names]


@app.get("/api/quota")
def quota():
    """Estimate today's Gemini free-tier use from Echo's execution logs (Pacific-day reset)."""
    pacific = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    settings = private_settings()
    profile_models = {}
    for config in connection_configs().values():
        for name, profile in config.get("profiles", {}).items():
            profile_models[name] = profile_model(profile, settings)
    usage = {}
    for log in sorted(LOGS.glob("*.jsonl")) if LOGS.is_dir() else []:
        try:
            lines = log.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("event") not in {"model_started", "model_failed"} or event.get("profile") in {None, "offline_fixture"}:
                continue
            when = datetime.fromisoformat(event["time_utc"]).astimezone(pacific)
            if when < day_start:
                continue
            model = profile_models.get(event["profile"], event["profile"])
            entry = usage.setdefault(model, {"model": model, "calls": 0, "quota_errors": 0})
            if event["event"] == "model_started":
                entry["calls"] += 1
            elif event.get("http_status") == 429:
                entry["quota_errors"] += 1
    reset = day_start + timedelta(days=1)
    return {"limit_per_model": FREE_TIER_DAILY_LIMIT, "resets_at": reset.isoformat(),
            "models": sorted(usage.values(), key=lambda item: -item["calls"]),
            "note": "Estimated from Echo run logs only; calls made outside Echo are not counted."}


# ---------- runs ----------

class RunRequest(BaseModel):
    manager_id: str = Field(min_length=1, max_length=40)
    start_date: str = SCOPE_MIN
    end_date: str = SCOPE_MAX
    question: str = Field(default="", max_length=2000)
    mode: str = Field(pattern="^(demo|live)$")
    profile: str | None = None
    use_local_split: bool = False
    model_call_limit: int = Field(default=32, ge=8, le=256)
    run_seconds: int = Field(default=900, ge=30, le=3600)


def summarize(run_id):
    path = RUNS / run_id
    meta_info = read_json(path / "meta.json", {})
    artifact = read_json(path / "artifact.json")
    if artifact:
        meta_info["result_status"] = artifact.get("status")
        meta_info["verification"] = (artifact.get("verification") or {}).get("decision")
        meta_info["api_calls"] = (artifact.get("execution") or {}).get("successful_generation_api_calls")
        meta_info["charts"] = len((artifact.get("visualization") or {}).get("files", []))
    return meta_info


def watch(run_id, process):
    code = process.wait()
    PROCESSES.pop(run_id, None)
    path = RUNS / run_id
    info = read_json(path / "meta.json", {})
    artifact = read_json(path / "artifact.json") or {}
    info["exit_code"] = code
    info["finished_at"] = datetime.now(timezone.utc).isoformat()
    info["state"] = "cancelled" if code == 130 else (artifact.get("status") or ("failed" if code else "complete"))
    write_json(path / "meta.json", info)


@app.post("/api/runs")
def start_run(request: RunRequest):
    try:
        AccessScope(request.manager_id, request.start_date, request.end_date)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if request.mode == "live" and not request.question.strip():
        raise HTTPException(400, "Live runs need a question.")
    if request.mode == "live" and request.use_local_split and not LOCAL_CONNECTIONS.is_file():
        raise HTTPException(400, "No connections.local.json exists for a per-agent model split.")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    path = RUNS / run_id
    path.mkdir(parents=True)
    command = [str(PYTHON if PYTHON.is_file() else sys.executable), "-u", "run_agent.py", "original",
               "--manager", request.manager_id, "--start", request.start_date, "--end", request.end_date,
               "--output", str(path / "artifact.json"), "--charts-dir", str(path / "charts")]
    if request.mode == "demo":
        command.append("--demo")
    else:
        command += ["--question", request.question.strip(),
                    "--model-call-limit", str(request.model_call_limit), "--run-seconds", str(request.run_seconds)]
        if request.use_local_split:
            command += ["--connections", str(LOCAL_CONNECTIONS)]
        elif request.profile:
            command += ["--profile", request.profile]
    info = {"id": run_id, "question": request.question.strip() if request.mode == "live" else
            "Review recognition using quarterly metrics and anonymous comments.",
            "typed_question": request.question.strip(), "manager_id": request.manager_id,
            "start_date": request.start_date, "end_date": request.end_date, "mode": request.mode,
            "profile": "per-agent split" if request.mode == "live" and request.use_local_split else
                       (request.profile if request.mode == "live" else "offline fixture"),
            "created_at": datetime.now(timezone.utc).isoformat(), "state": "running"}
    write_json(path / "meta.json", info)
    output = (path / "console.txt").open("w", encoding="utf-8")
    process = subprocess.Popen(command, cwd=ECHO, stdout=output, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    output.close()
    PROCESSES[run_id] = process
    threading.Thread(target=watch, args=(run_id, process), daemon=True).start()
    return info


@app.get("/api/runs")
def list_runs():
    runs = [summarize(path.name) for path in RUNS.iterdir() if (path / "meta.json").is_file()]
    return sorted(runs, key=lambda item: item.get("created_at", ""), reverse=True)


def without_comment_text(artifact):
    """Manager view: keep comment citations but never send comment text to the browser."""
    if not artifact:
        return artifact

    def clean(items):
        return [{"citation_id": item["citation_id"], "source": item.get("source"), "anonymous": True, "redacted": True}
                if item.get("source") == "HR_survey_comments" else item for item in items or []]

    # Allow-list only what the manager page renders; traces and retrieval logs can carry comment text.
    visualization = artifact.get("visualization") or {}
    return {
        "question": artifact.get("question"), "answer": artifact.get("answer", ""),
        "status": artifact.get("status"), "mode": artifact.get("mode"), "scope": artifact.get("scope"),
        "evidence": clean(artifact.get("evidence")),
        "delegations": [{"agent": d.get("agent"), "evidence": clean(d.get("evidence"))} for d in artifact.get("delegations") or []],
        "visualization": {"charts": visualization.get("charts", []), "reason": visualization.get("reason", "")},
        "verification": {"decision": (artifact.get("verification") or {}).get("decision")},
        "limitations": artifact.get("limitations", []),
        "findings": [], "next_steps": [], "clarification_questions": [], "sentiment": {}, "execution": {},
    }


@app.get("/api/runs/{run_id}")
def get_run(run_id: str, view: str = "technical"):
    path = run_dir(run_id)
    info = summarize(run_id)
    artifact = read_json(path / "artifact.json")
    if view == "manager":
        return {"meta": info, "artifact": without_comment_text(artifact), "console": ""}
    console = (path / "console.txt").read_text(encoding="utf-8", errors="replace") if (path / "console.txt").is_file() else ""
    return {"meta": info, "artifact": artifact, "console": console}


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str):
    path = run_dir(run_id)
    if run_id in PROCESSES:
        raise HTTPException(409, "Cancel the run before deleting it.")
    import shutil
    shutil.rmtree(path)
    return {"deleted": run_id}


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str):
    run_dir(run_id)
    process = PROCESSES.get(run_id)
    if not process:
        raise HTTPException(409, "This run is not active.")
    process.send_signal(signal.SIGINT)
    return {"cancelling": run_id}


@app.get("/api/runs/{run_id}/files/{name}")
def run_file(run_id: str, name: str):
    charts = (run_dir(run_id) / "charts").resolve()
    target = (charts / name).resolve()
    if target.parent != charts or not target.is_file() or target.suffix not in {".svg", ".csv", ".json"}:
        raise HTTPException(404, "Unknown file.")
    return FileResponse(target)


def log_path(path):
    console = path / "console.txt"
    try:
        first = console.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return None
    return Path(first.split(": ", 1)[1]) if first.startswith("Execution log: ") else None


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str, request: Request, pace_ms: int = 0):
    """Server-sent events: each Echo execution-log line, then a final `done` event."""
    path = run_dir(run_id)

    async def stream():
        log, position, waited = None, 0, 0.0
        while True:
            if await request.is_disconnected():
                return
            active = run_id in PROCESSES
            log = log or log_path(path)
            if log and log.is_file():
                with log.open(encoding="utf-8") as handle:
                    handle.seek(position)
                    chunk = handle.read()
                    position = handle.tell()
                for line in chunk.splitlines():
                    if line.strip():
                        yield f"event: log\ndata: {line}\n\n"
                        # Offline demos finish instantly; pacing replays them as a readable timeline.
                        if pace_ms:
                            await asyncio.sleep(pace_ms / 1000)
            if not active and (log is not None or waited > 5):
                yield f"event: done\ndata: {json.dumps(summarize(run_id))}\n\n"
                return
            await asyncio.sleep(0.4)
            waited += 0.4

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------- built frontend ----------

if FRONTEND.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        target = (FRONTEND / path).resolve()
        if path and target.is_file() and FRONTEND.resolve() in target.parents:
            return FileResponse(target)
        # Never cache the page shell, so a rebuilt frontend shows up on the next load.
        return FileResponse(FRONTEND / "index.html", headers={"Cache-Control": "no-cache"})
