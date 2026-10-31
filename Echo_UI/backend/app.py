"""Echo UI backend: a thin local API around the existing Echo command-line workflow.

Echo itself is not modified. Each analysis runs `Agent_Echo/run_agent.py` as a subprocess, so the
UI gets exactly the same scope checks, evidence rules and verification as the terminal. Progress is
streamed to the browser from Echo's own JSONL execution log.
"""

import asyncio
import io
import re
import shutil
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
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
ECHO = ROOT / "Agent_Echo"
DATABASE = ECHO / "data" / "echo.db"
LOGS = ECHO / "reports" / "logs"
DICTIONARY = ROOT / "files_update" / "QA_data_dictionary.csv"
RUNS = Path(__file__).resolve().parents[1] / "runs"
CACHE = Path(__file__).resolve().parents[1] / "cache"
RECORDINGS = CACHE / "recordings.json"
FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "dist"
PYTHON = ECHO / ".venv" / "bin" / "python"
LOCAL_CONNECTIONS = ECHO / "connections.local.json"
SCOPE_MIN, SCOPE_MAX = "2024-10-01", "2026-09-30"
FREE_TIER_DAILY_LIMIT = 20

sys.path.insert(0, str(ECHO))
from agents.data_access import AccessScope, ScopedData  # noqa: E402
from pulse import pulse as build_pulse  # noqa: E402
import offline  # noqa: E402

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


@app.get("/api/managers/{manager_id}/pulse")
def manager_pulse(manager_id: str, start: str = SCOPE_MIN, end: str = SCOPE_MAX, generate: bool = False):
    """Survey mood per topic, plus cached AI theme bullets (generated on request, one model call)."""
    try:
        scope = AccessScope(manager_id, start, end)
        data = ScopedData(DATABASE, scope)
    except ValueError as error:
        raise HTTPException(400, str(error))
    try:
        settings = private_settings()
        key = os.getenv("GOOGLE_API_KEY") or settings.get("GOOGLE_API_KEY")
        return build_pulse(data, scope, CACHE, api_key=key, generate=generate)
    finally:
        data.close()


@app.get("/api/managers/{manager_id}/updates")
def manager_updates(manager_id: str, start: str = SCOPE_MIN, end: str = SCOPE_MAX):
    """Side panel data: latest-quarter changes, recognition gaps and goal measures (deterministic, no model calls)."""
    try:
        scope = AccessScope(manager_id, start, end)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if not DATABASE.is_file():
        raise HTTPException(503, "Echo's database is missing. Run Agent_Echo/import_data.py first.")
    q = offline.Query(DATABASE, scope)
    try:
        return offline.team_updates(q)
    finally:
        q.close()


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


def question_key(question):
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()


def recording_key(manager_id, start, end, question):
    return f"{manager_id.upper()}|{start}|{end}|{question_key(question)}"


def recordings():
    return read_json(RECORDINGS, {})


def save_recording(info):
    """Keep the latest verified live answer per manager, period and question for demo replay."""
    CACHE.mkdir(parents=True, exist_ok=True)
    saved = recordings()
    saved[recording_key(info["manager_id"], info["start_date"], info["end_date"], info["question"])] = {
        "run_id": info["id"], "question": info["question"], "recorded_at": info.get("finished_at")}
    write_json(RECORDINGS, saved)


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
    if info.get("mode") == "live" and info["state"] == "complete" and (artifact.get("verification") or {}).get("decision") == "accept":
        save_recording(info)


def offline_run(run_id, path, request):
    """Demo mode without a saved answer: real numbers for suggested questions, templated wording, no AI."""
    scope = AccessScope(request.manager_id, request.start_date, request.end_date)
    built = offline.build(DATABASE, scope, request.question.strip()) or offline.unsupported(scope, request.question.strip())
    artifact, log = built
    write_json(path / "artifact.json", artifact)
    (path / "log.jsonl").write_text("\n".join(json.dumps(event) for event in log) + "\n", encoding="utf-8")
    (path / "console.txt").write_text(f"Execution log: {path / 'log.jsonl'}\nOffline demo answer (no AI).\n", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    info = {"id": run_id, "question": request.question.strip(), "typed_question": request.question.strip(),
            "manager_id": request.manager_id, "start_date": request.start_date, "end_date": request.end_date,
            "mode": "offline", "profile": "offline demo (no AI)", "created_at": now, "finished_at": now,
            "state": artifact["status"], "exit_code": 0}
    write_json(path / "meta.json", info)
    return info


def replay_run(run_id, path, request, recording):
    """Demo mode with a saved answer: copy a verified live run so it replays without any API calls."""
    source = RUNS / recording["run_id"]
    shutil.copy(source / "artifact.json", path / "artifact.json")
    if (source / "charts").is_dir():
        shutil.copytree(source / "charts", path / "charts")
    original_log = log_path(source)
    if original_log and original_log.is_file():
        shutil.copy(original_log, path / "log.jsonl")
    (path / "console.txt").write_text(f"Execution log: {path / 'log.jsonl'}\nReplayed from saved live run {recording['run_id']}.\n",
                                      encoding="utf-8")
    source_meta = read_json(source / "meta.json", {})
    info = {"id": run_id, "question": recording["question"], "typed_question": request.question.strip(),
            "manager_id": request.manager_id, "start_date": request.start_date, "end_date": request.end_date,
            "mode": "replay", "profile": source_meta.get("profile", "saved live run"), "replay_of": recording["run_id"],
            "recorded_at": recording.get("recorded_at"), "created_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(), "state": source_meta.get("state", "complete"), "exit_code": 0}
    write_json(path / "meta.json", info)
    return info


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
    # Questions that try to unmask anonymous respondents are declined in every mode, before any data is read.
    if offline.guarded(request.question):
        return offline_run(run_id, path, request)
    if request.mode == "demo" and request.question.strip():
        recording = recordings().get(recording_key(request.manager_id, request.start_date, request.end_date, request.question))
        if recording and (RUNS / recording["run_id"] / "artifact.json").is_file():
            return replay_run(run_id, path, request, recording)
        return offline_run(run_id, path, request)
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


@app.get("/api/recordings")
def list_recordings(manager_id: str, start: str = SCOPE_MIN, end: str = SCOPE_MAX):
    prefix = f"{manager_id.upper()}|{start}|{end}|"
    return [{"question": item["question"], "recorded_at": item.get("recorded_at")}
            for key, item in recordings().items() if key.startswith(prefix) and (RUNS / item["run_id"]).is_dir()]


def how_it_was_made(artifact):
    """Counts only, for the manager's one-line 'How this answer was made'."""
    evidence = list(artifact.get("evidence") or []) + [e for d in artifact.get("delegations") or [] for e in d.get("evidence") or []]
    ids = {}
    for item in evidence:
        ids.setdefault(item.get("citation_id"), item)
    verification = artifact.get("verification") or {}
    return {
        "specialists": sorted({d.get("agent") for d in artifact.get("delegations") or [] if d.get("agent")}),
        "queries": sum(1 for e in ids.values() if isinstance(e.get("sql"), str)),
        "survey_sources": sum(1 for e in ids.values() if e.get("source") == "HR_survey_comments"),
        "sentiment_runs": len(artifact.get("sentiment") or {}),
        "charts": len((artifact.get("visualization") or {}).get("charts") or []),
        "findings_checked": len(artifact.get("findings") or []),
        "drafts_checked": verification.get("drafts_checked") or len(verification.get("reviews") or []),
        "completed_reviews": verification.get("completed_reviews", len(verification.get("reviews") or [])),
        "review_status": verification.get("status", "completed"),
    }


def without_comment_text(artifact):
    """Manager view: keep comment citations but never send comment text to the browser."""
    if not artifact:
        return artifact

    def clean(items):
        return [{"citation_id": item["citation_id"], "source": item.get("source"), "anonymous": True, "redacted": True}
                if item.get("source") == "HR_survey_comments" else item for item in items or []]

    # Allow-list only what the manager page renders; traces and retrieval logs can carry comment text.
    visualization = artifact.get("visualization") or {}
    verification = artifact.get("verification") or {}
    return {
        "question": artifact.get("question"), "answer": artifact.get("answer", ""),
        "status": artifact.get("status"), "mode": artifact.get("mode"), "scope": artifact.get("scope"),
        "evidence": clean(artifact.get("evidence")),
        "delegations": [{"agent": d.get("agent"), "evidence": clean(d.get("evidence"))} for d in artifact.get("delegations") or []],
        "visualization": {"charts": visualization.get("charts", []), "reason": visualization.get("reason", "")},
        "verification": {key: verification.get(key) for key in
                         ("decision", "status", "completed_reviews", "latest_candidate_id", "released_candidate_id")},
        "limitations": artifact.get("limitations", []),
        "findings": [{"finding_id": f.get("finding_id"), "text": f.get("text"), "citation_ids": f.get("citation_ids", []),
                      "status": f.get("status")} for f in artifact.get("findings") or []],
        "next_steps": artifact.get("next_steps", []), "clarification_questions": [], "sentiment": {}, "execution": {},
        "made": how_it_was_made(artifact),
        # Story fields from offline answers (counts, record-level work items and checks; never survey text).
        **{key: artifact[key] for key in ("triangle", "examples", "watch", "voice", "guardrail", "impact") if key in artifact},
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


def chart_table(run_id, source_id):
    """The rows behind one of a run's charts, limited to the columns that chart plots (never other fields)."""
    artifact = read_json(run_dir(run_id) / "artifact.json") or {}
    charts = (artifact.get("visualization") or {}).get("charts") or []
    spec = next((c for c in charts if c.get("source_id") == source_id), None)
    if spec is None:
        raise HTTPException(404, "This run has no chart for that source.")
    evidence = list(artifact.get("evidence") or []) + [e for d in artifact.get("delegations") or [] for e in d.get("evidence") or []]
    source = next((e for e in evidence if e.get("citation_id") == source_id and isinstance(e.get("sql"), str)), None)
    if source is None or source.get("source") == "HR_survey_comments":
        raise HTTPException(404, "The chart's source rows are not available.")
    columns = [c for c in (spec.get("x"), spec.get("series"), spec.get("y"), spec.get("denominator")) if c]
    columns = list(dict.fromkeys(c for c in columns if any(c in row for row in source.get("rows") or [])))
    return spec, columns, [[row.get(c) for c in columns] for row in source.get("rows") or []]


def safe_filename(text):
    return re.sub(r"[^A-Za-z0-9 ._-]+", "", text or "chart").strip()[:80] or "chart"


@app.get("/api/runs/{run_id}/charts/{source_id}/data.csv")
def chart_csv(run_id: str, source_id: str):
    """CSV of one chart's plotted values, for Power BI or a spreadsheet."""
    spec, columns, rows = chart_table(run_id, source_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    name = safe_filename(f"Echo - {spec.get('title')}") + ".csv"
    return Response(buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---------- Shared chart story (used by the Power BI, Tableau and Excel exports) ----------

def chart_story(spec, artifact, info, x_col, y_col, series_col, bar):
    """The description that travels with an exported chart: [(heading, lines, as bullets)], plus a closing note."""
    cite = re.compile(r"\s*\[[A-Za-z]+\d*(?::[A-Za-z0-9_-]+)?\]")
    findings = [cite.sub("", f.get("text", "")).strip() for f in artifact.get("findings") or []
                if f.get("status", "supported") == "supported" and spec["source_id"] in (f.get("citation_ids") or [])]
    if not findings:
        findings = [cite.sub("", f.get("text", "")).strip() for f in artifact.get("findings") or [] if f.get("status", "supported") == "supported"]
    verified = (artifact.get("verification") or {}).get("decision") == "accept" and artifact.get("status") == "complete"
    shows = (f"{y_col} by {x_col.lower()}" + (f", one {'line' if not bar else 'colour'} per {series_col.lower()}" if series_col else "") + "."
             + (f" Unit: {spec['unit']}." if spec.get("unit") else ""))
    sections = [("The question", [artifact.get("question") or info.get("question") or ""], False),
                ("What this chart shows", [shows], False)]
    for heading, lines in (("What Echo found", findings[:3]), ("Why it matters", (artifact.get("impact") or [])[:2]),
                           ("What to do first", (artifact.get("next_steps") or [])[:2]), ("Before you act", (artifact.get("limitations") or [])[:2])):
        if lines:
            sections.append((heading, lines, True))
    footer = (("Checked by ZeroSugar, Echo's fact-checker, before release. " if verified else "Not fully verified: read with care. ")
              + "Team-level numbers only; no individual survey responses.")
    return sections, footer


def export_context(run_id, source_id):
    """Everything an export needs: the chart spec, the run's artifact and meta, the team name and the plotted rows."""
    spec, _, _ = chart_table(run_id, source_id)
    path = run_dir(run_id)
    artifact = read_json(path / "artifact.json") or {}
    info = read_json(path / "meta.json", {})
    team = info.get("manager_id", "")
    try:
        with database() as db:
            row = db.execute("SELECT Primary_Team FROM HR_managers WHERE Manager_ID = ?", (info.get("manager_id"),)).fetchone()
            team = row[0] if row else team
    except HTTPException:
        pass
    evidence = list(artifact.get("evidence") or []) + [e for d in artifact.get("delegations") or [] for e in d.get("evidence") or []]
    source = next(e for e in evidence if e.get("citation_id") == source_id)
    rows = [r for r in source.get("rows") or [] if r.get(spec["y"]) is not None]
    return spec, artifact, info, team, rows


def export_name(title):
    """A short file/folder name: Windows paths are limited to 260 characters and Extract All repeats the zip name."""
    folder = safe_filename(f"Echo - {title}")
    if len(folder) > 44:
        words = folder[:45].rsplit(" ", 1)[0].rstrip(" -,").split(" ")
        while len(words) > 3 and words[-1].lower() in {"a", "an", "the", "of", "to", "by", "and", "or", "than", "over", "with", "without", "for", "in", "on"}:
            words.pop()
        folder = " ".join(words)
    return folder


# ---------- Power BI project export ----------
# A chart becomes a small Power BI Project (PBIP: PBIR report + TMDL model, generally available in
# Power BI Desktop since September 2026). The plotted values are embedded in a DAX DATATABLE, so the
# project opens without Echo running and without data source credentials. Only the chart's own
# columns are included, never survey comment text.

PBI_PALETTE = ["#8FA066", "#7F97B5", "#D98A99", "#E0A267", "#9C8FCB", "#6FB39A", "#D2B356", "#78A9CF"]
PBI_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
PBI_VISUAL = f"{PBI_SCHEMA}/item/report/definition/visualContainer/2.9.0/schema.json"


def pbi_id(*parts):
    """Stable 20-hex-character object name, as Power BI uses for pages and visuals."""
    return uuid.uuid5(uuid.NAMESPACE_URL, "echo/" + "/".join(parts)).hex[:20]


def pbi_label(text, used):
    """A readable model column name from a chart label; unique within the table."""
    name = re.sub(r"[^A-Za-z0-9 ()%&/,-]+", " ", str(text or "")).strip()
    name = re.sub(r"\s+", " ", name)[:60] or "Value"
    candidate, n = name, 2
    while candidate.lower() in used:
        candidate, n = f"{name} {n}", n + 1
    used.add(candidate.lower())
    return candidate


def tmdl_name(name):
    return "'" + name.replace("'", "''") + "'" if re.search(r"[^A-Za-z0-9_]", name) else name


def dax_text(value):
    return '"' + str(value).replace('"', '""') + '"'


def literal(value):
    return {"expr": {"Literal": {"Value": value}}}


def textbox(name, position, paragraphs):
    return {
        "$schema": PBI_VISUAL, "name": name, "position": position,
        "visual": {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
            "visualContainerObjects": {"background": [{"properties": {"show": literal("false")}}],
                                       "border": [{"properties": {"show": literal("false")}}]},
            "drillFilterOtherVisuals": True,
        },
    }


def runs(*items):
    """Paragraph text runs: (text, size, colour, bold)."""
    return [{"value": text, "textStyle": {"fontFamily": "Segoe UI Semibold" if bold else "Segoe UI", "fontSize": f"{size}pt", "color": colour}}
            for text, size, colour, bold in items]


def column_field(table, column):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}}


def build_powerbi_project(run_id, spec, artifact, info, team):
    """Return (folder name, {relative path: text}) for a PBIP project that opens straight to the chart."""
    evidence = list(artifact.get("evidence") or []) + [e for d in artifact.get("delegations") or [] for e in d.get("evidence") or []]
    source = next(e for e in evidence if e.get("citation_id") == spec["source_id"])
    rows = [r for r in source.get("rows") or [] if r.get(spec["y"]) is not None]
    table = "Chart data"
    used = {"order", "colour", "bar colour"}
    x_col = pbi_label(spec.get("x_label") or spec["x"], used)
    y_col = pbi_label(spec.get("y_label") or spec["y"], used)
    series_col = pbi_label(spec["series"], used) if spec.get("series") and any(spec["series"] in r for r in rows) else None
    n_col = pbi_label(spec["denominator"], used) if spec.get("denominator") and any(spec["denominator"] in r for r in rows) else None
    bar = spec.get("kind") == "bar"
    single = series_col is None

    # Category order exactly as Echo drew it; a hidden Order column keeps Power BI from sorting alphabetically.
    order = {}
    for r in rows:
        order.setdefault(str(r.get(spec["x"])), len(order) + 1)
    columns = [(x_col, "STRING"), ("Order", "INTEGER"), (y_col, "DOUBLE")]
    if series_col:
        columns.append((series_col, "STRING"))
    if n_col:
        columns.append((n_col, "DOUBLE"))
    columns.append(("Colour", "STRING"))

    def number(value):
        try:
            return repr(float(value))
        except (TypeError, ValueError):
            return "0"

    data_rows = []
    for r in rows:
        x = str(r.get(spec["x"]))
        cells = [dax_text(x), str(order[x]), number(r.get(spec["y"]))]
        if series_col:
            cells.append(dax_text(r.get(spec["series"], "")))
        if n_col:
            cells.append(number(r.get(spec["denominator"])))
        cells.append(dax_text(PBI_PALETTE[(order[x] - 1) % len(PBI_PALETTE)]))
        data_rows.append("{" + ", ".join(cells) + "}")
    datatable = ("DATATABLE(\n" + ",\n".join(f"\t\t\t\t\t{dax_text(n)}, {t}" for n, t in columns) + ",\n\t\t\t\t\t{\n"
                 + ",\n".join("\t\t\t\t\t\t" + row for row in data_rows) + "\n\t\t\t\t\t}\n\t\t\t\t)")

    def tmdl_column(name, dtype, hidden=False, sort_by=None, fmt=None):
        lines = [f"\tcolumn {tmdl_name(name)}", f"\t\tdataType: {dtype}"]
        if hidden:
            lines.append("\t\tisHidden")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines += ["\t\tsummarizeBy: none", f"\t\tsourceColumn: [{name}]"]
        if sort_by:
            lines.append(f"\t\tsortByColumn: {tmdl_name(sort_by)}")
        return "\n".join(lines) + "\n"

    table_tmdl = (f"/// {spec.get('title', 'Echo chart')} (exported from Echo run {run_id})\n"
                  f"table {tmdl_name(table)}\n\n"
                  f"\t/// Pastel colour for each category, used to colour the bars.\n"
                  f"\tmeasure 'Bar colour' = SELECTEDVALUE({tmdl_name(table)}[Colour])\n\n"
                  + tmdl_column(x_col, "string", sort_by="Order") + "\n"
                  + tmdl_column("Order", "int64", hidden=True, fmt="0") + "\n"
                  + tmdl_column(y_col, "double", fmt="#,##0.##") + "\n"
                  + (tmdl_column(series_col, "string") + "\n" if series_col else "")
                  + (tmdl_column(n_col, "double", fmt="#,##0") + "\n" if n_col else "")
                  + tmdl_column("Colour", "string", hidden=True) + "\n"
                  + f"\tpartition {tmdl_name(table)} = calculated\n\t\tmode: import\n\t\tsource =\n\t\t\t\t{datatable}\n")

    title = spec.get("title") or "Echo chart"
    folder = export_name(title)
    model, report = "EchoChart.SemanticModel", "EchoChart.Report"
    page = pbi_id(run_id, spec["source_id"], "page")
    x_field = column_field(table, x_col)
    y_field = {"Aggregation": {"Expression": column_field(table, y_col), "Function": 0}}
    query = {
        "queryState": {
            "Category": {"projections": [{"field": x_field, "queryRef": f"{table}.{x_col}", "nativeQueryRef": x_col, "active": True}]},
            "Y": {"projections": [{"field": y_field, "queryRef": f"Sum({table}.{y_col})", "nativeQueryRef": f"Sum of {y_col}", "displayName": y_col}]},
        },
        "sortDefinition": {"sort": [{"field": x_field, "direction": "Ascending"}], "isDefaultSort": True},
    }
    if series_col:
        query["queryState"]["Series"] = {"projections": [{"field": column_field(table, series_col), "queryRef": f"{table}.{series_col}", "nativeQueryRef": series_col}]}
    chart_objects = {
        "labels": [{"properties": {"show": literal("true")}}],
        "legend": [{"properties": {"show": literal("false" if single else "true"), "position": literal("'Top'")}}],
        "categoryAxis": [{"properties": {"titleText": literal("'" + x_col.replace("'", "''") + "'")}}],
        "valueAxis": [{"properties": {"titleText": literal("'" + y_col.replace("'", "''") + "'")}}],
    }
    if bar and single:
        chart_objects["dataPoint"] = [
            {"properties": {}},
            {"properties": {"fill": {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": "Bar colour"}}}}}},
             "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}},
        ]
    if not bar:
        chart_objects["markers"] = [{"properties": {"show": literal("true")}}]
    chart = {
        "$schema": PBI_VISUAL, "name": pbi_id(run_id, spec["source_id"], "chart"),
        "position": {"x": 32, "y": 112, "z": 1000, "height": 576, "width": 800, "tabOrder": 1000},
        "visual": {
            "visualType": "clusteredColumnChart" if bar else "lineChart",
            "query": query,
            "objects": chart_objects,
            "visualContainerObjects": {"title": [{"properties": {"show": literal("true"), "text": literal("'" + f"{y_col} by {x_col}".replace("'", "''") + "'")}}]},
            "drillFilterOtherVisuals": True,
        },
    }
    table_projections = [{"field": column_field(table, c), "queryRef": f"{table}.{c}", "nativeQueryRef": c} for c in [x_col, series_col, y_col, n_col] if c]
    data_table = {
        "$schema": PBI_VISUAL, "name": pbi_id(run_id, spec["source_id"], "table"),
        "position": {"x": 856, "y": 488, "z": 2000, "height": 200, "width": 392, "tabOrder": 2000},
        "visual": {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": table_projections}}},
            "objects": {"columnHeaders": [{"properties": {"columnAdjustment": literal("'growToFit'"), "autoSizeColumnWidth": literal("true")}}]},
            "visualContainerObjects": {"title": [{"properties": {"show": literal("true"), "text": literal("'The numbers behind the chart'")}}]},
            "drillFilterOtherVisuals": True,
        },
    }

    ink, muted = "#1E2630", "#526174"
    sections, footer = chart_story(spec, artifact, info, x_col, y_col, series_col, bar)
    description = []
    for heading, lines, bullets in sections:
        description.append({"textRuns": runs((heading, 11, ink, True))})
        description += [{"textRuns": runs((text, 10, muted, False)), **({"listType": "bullet"} if bullets else {})} for text in lines]
    description.append({"textRuns": runs((footer, 9, muted, False))})
    period = f"{info.get('start_date')} to {info.get('end_date')}"
    visuals = {
        "title": textbox(pbi_id(run_id, spec["source_id"], "title"), {"x": 32, "y": 20, "z": 3000, "height": 52, "width": 1216, "tabOrder": 0},
                         [{"textRuns": runs((title, 22, ink, True))}]),
        "subtitle": textbox(pbi_id(run_id, spec["source_id"], "subtitle"), {"x": 32, "y": 70, "z": 3001, "height": 32, "width": 1216, "tabOrder": 1},
                            [{"textRuns": runs((f"{team} · manager {info.get('manager_id')} · {period} · exported from Echo on {date.today().isoformat()}", 11, muted, False))}]),
        "chart": chart,
        "about": textbox(pbi_id(run_id, spec["source_id"], "about"), {"x": 856, "y": 112, "z": 3002, "height": 364, "width": 392, "tabOrder": 1500}, description),
        "table": data_table,
    }

    theme = {"name": "Echo", "dataColors": PBI_PALETTE, "background": "#FFFFFF", "foreground": ink, "tableAccent": "#727E54"}
    report_json = {
        "$schema": f"{PBI_SCHEMA}/item/report/definition/report/3.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU10", "reportVersionAtImport": {"visual": "1.8.97", "report": "2.0.97", "page": "1.3.97"}, "type": "SharedResources"},
            "customTheme": {"name": "EchoTheme.json", "reportVersionAtImport": {"visual": "1.8.97", "report": "2.0.97", "page": "1.3.97"}, "type": "RegisteredResources"},
        },
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources", "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": "EchoTheme.json", "path": "EchoTheme.json", "type": "CustomTheme"}]},
        ],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True, "useEnhancedTooltips": True},
    }
    platform = lambda kind: {"$schema": f"{PBI_SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
                             "metadata": {"type": kind, "displayName": title[:100]},
                             "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"echo/{run_id}/{spec['source_id']}/{kind}"))}}
    dump = lambda value: json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    files = {
        f"{folder}.pbip": dump({"$schema": f"{PBI_SCHEMA}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                                "artifacts": [{"report": {"path": report}}], "settings": {"enableAutoRecovery": True}}),
        f"{model}/.platform": dump(platform("SemanticModel")),
        f"{model}/definition.pbism": dump({"$schema": f"{PBI_SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "4.2", "settings": {}}),
        f"{model}/definition/database.tmdl": "database\n\tcompatibilityLevel: 1702\n",
        f"{model}/definition/model.tmdl": ("model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n"
                                           "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
                                           f"ref table {tmdl_name(table)}\n"),
        f"{model}/definition/tables/{table}.tmdl": table_tmdl,
        f"{report}/.platform": dump(platform("Report")),
        f"{report}/definition.pbir": dump({"$schema": f"{PBI_SCHEMA}/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0",
                                          "datasetReference": {"byPath": {"path": f"../{model}"}}}),
        f"{report}/definition/version.json": dump({"$schema": f"{PBI_SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}),
        f"{report}/definition/report.json": dump(report_json),
        f"{report}/definition/pages/pages.json": dump({"$schema": f"{PBI_SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
                                                       "pageOrder": [page], "activePageName": page}),
        f"{report}/definition/pages/{page}/page.json": dump({"$schema": f"{PBI_SCHEMA}/item/report/definition/page/1.4.0/schema.json",
                                                            "name": page, "displayName": "Echo chart", "displayOption": "FitToPage", "height": 720, "width": 1280}),
        f"{report}/StaticResources/RegisteredResources/EchoTheme.json": dump(theme),
    }
    for key, visual in visuals.items():
        files[f"{report}/definition/pages/{page}/visuals/{visual['name']}/visual.json"] = dump(visual)
    files["How to open.txt"] = (f"{title}\r\n\r\nRight-click the downloaded zip, choose Extract All, then double-click \"{folder}.pbip\".\r\n"
                                "The page opens with the chart, a description and the numbers behind it.\r\n"
                                "If the visuals look empty, choose Refresh on the Home ribbon once.\r\n"
                                "Needs a Power BI Desktop release from September 2026 or later (Power BI Project format).\r\n")
    return folder, files


@app.get("/api/runs/{run_id}/charts/{source_id}/powerbi.zip")
def chart_powerbi(run_id: str, source_id: str):
    """A zipped Power BI Project that opens directly to this chart, with its description and data."""
    import zipfile
    spec, artifact, info, team, _ = export_context(run_id, source_id)
    folder, files = build_powerbi_project(run_id, spec, artifact, info, team)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in files.items():
            # Files sit at the zip root, so Windows "Extract All" makes exactly one folder named after the zip.
            archive.writestr(name, text.encode("utf-8"))
    return Response(buffer.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{folder}.zip"'})


# ---------- Tableau packaged workbook export ----------
# A .twbx is a zip holding the workbook XML and its data file. The XML follows Tableau's published
# TWB schema for 2026.1 (github.com/tableau/tableau-document-schemas), so Tableau 2026.1 or newer
# is needed. Only the chart's own columns go into the data file, never survey comment text.

def tableau_twb(title, subtitle, sections, x_col, y_col, series_col, n_col, rows, bar, palette, csv_name="chart.csv"):
    """Tableau workbook XML (schema 26.1) for one chart; rows are dicts keyed by the CSV column names.
    The description travels as the worksheet title and caption."""
    import xml.etree.ElementTree as ET
    E, S = ET.Element, ET.SubElement
    ds = "federated.echo"
    cols = [(x_col, "string")] + ([(series_col, "string")] if series_col else []) + [(y_col, "real")] + ([(n_col, "real")] if n_col else [])
    wb = E("workbook", {"original-version": "26.1", "source-build": "0.0.0 (0000.0.0.0)", "source-platform": "win", "version": "26.1",
                        "xmlns:user": "http://www.tableausoftware.com/xml/user"})
    S(S(wb, "document-format-change-manifest"), "ManifestByVersion")
    prefs = S(wb, "preferences")
    pal = S(prefs, "color-palette", {"name": "Echo pastels", "type": "regular"})
    for c in palette:
        S(pal, "color").text = c.lower()
    dss = S(wb, "datasources")
    d = S(dss, "datasource", {"caption": "Echo chart data", "inline": "true", "name": ds, "version": "26.1"})
    conn = S(d, "connection", {"class": "federated"})
    named = S(S(conn, "named-connections"), "named-connection", {"caption": "chart", "name": "textscan.echo"})
    S(named, "connection", {"class": "textscan", "directory": "Data/Datafiles", "filename": csv_name, "password": "", "server": ""})
    rel = S(conn, "relation", {"connection": "textscan.echo", "name": csv_name, "table": "[" + csv_name.replace(".", "#") + "]", "type": "table"})
    rc = S(rel, "columns", {"character-set": "UTF-8", "header": "yes", "locale": "en_US", "separator": ","})
    for i, (n, t) in enumerate(cols):
        S(rc, "column", {"datatype": t, "name": n, "ordinal": str(i)})
    mr = S(conn, "metadata-records")
    for i, (n, t) in enumerate(cols):
        m = S(mr, "metadata-record", {"class": "column"})
        for tag, val in [("remote-name", n), ("remote-type", "5" if t == "real" else "129"), ("local-name", f"[{n}]"), ("parent-name", f"[{csv_name}]"),
                         ("remote-alias", n), ("ordinal", str(i)), ("local-type", t), ("aggregation", "Sum" if t == "real" else "Count"), ("contains-null", "true")]:
            S(m, tag).text = val
    S(d, "aliases", {"enabled": "yes"})
    for n, t in cols:
        S(d, "column", {"datatype": t, "name": f"[{n}]", "role": "measure" if t == "real" else "dimension", "type": "quantitative" if t == "real" else "nominal"})

    sheet = title[:90] or "Echo chart"
    ws = S(S(wb, "worksheets"), "worksheet", {"name": sheet})
    lo = S(ws, "layout-options")
    ft = S(S(lo, "title"), "formatted-text")
    S(ft, "run", {"bold": "true", "fontsize": "16"}).text = title
    S(ft, "run").text = "Æ\n"
    S(ft, "run", {"fontcolor": "#526174", "fontsize": "10"}).text = subtitle
    cap = S(S(lo, "caption"), "formatted-text")
    first = True
    for heading, lines, *_ in sections:
        S(cap, "run", {"bold": "true"}).text = ("" if first else "Æ\n") + heading
        for line in lines:
            S(cap, "run").text = "Æ\n• " + line
        first = False
    table = S(ws, "table")
    view = S(table, "view")
    S(S(view, "datasources"), "datasource", {"caption": "Echo chart data", "name": ds})
    dep = S(view, "datasource-dependencies", {"datasource": ds})
    for n, t in cols:
        S(dep, "column", {"datatype": t, "name": f"[{n}]", "role": "measure" if t == "real" else "dimension", "type": "quantitative" if t == "real" else "nominal"})
    xi, yi = f"[none:{x_col}:nk]", f"[sum:{y_col}:qk]"
    si = f"[none:{series_col}:nk]" if series_col else None
    S(dep, "column-instance", {"column": f"[{x_col}]", "derivation": "None", "name": xi, "pivot": "key", "type": "nominal"})
    if si:
        S(dep, "column-instance", {"column": f"[{series_col}]", "derivation": "None", "name": si, "pivot": "key", "type": "nominal"})
    S(dep, "column-instance", {"column": f"[{y_col}]", "derivation": "Sum", "name": yi, "pivot": "key", "type": "quantitative"})
    S(view, "aggregation", {"value": "true"})
    colour_by = si or (xi if bar else None)
    style = S(table, "style")
    if colour_by:
        key = series_col or x_col
        seen = []
        for r in rows:
            v = str(r[key])
            if v not in seen:
                seen.append(v)
        enc = S(S(style, "style-rule", {"element": "mark"}), "encoding", {"attr": "color", "field": f"[{ds}].{colour_by}", "palette": "Echo pastels", "type": "palette"})
        for i, v in enumerate(seen):
            S(S(enc, "map", {"to": palette[i % len(palette)].lower()}), "bucket").text = f'"{v}"'
    pane = S(S(table, "panes"), "pane", {"selection-relaxation-option": "selection-relaxation-allow"})
    S(S(pane, "view"), "breakdown", {"value": "auto"})
    S(pane, "mark", {"class": "Bar" if bar else "Line"})
    if colour_by:
        S(S(pane, "encodings"), "color", {"column": f"[{ds}].{colour_by}"})
    S(table, "rows").text = f"[{ds}].{yi}"
    S(table, "cols").text = f"[{ds}].{xi}"
    S(ws, "simple-id", {"uuid": "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "echo/tableau/" + title)).upper() + "}"})
    win = S(S(wb, "windows"), "window", {"class": "worksheet", "maximized": "true", "name": sheet})
    cards = S(win, "cards")
    S(S(S(cards, "edge", {"name": "left"}), "strip", {"size": "160"}), "card", {"type": "pages"})
    S(S(S(cards, "edge", {"name": "top"}), "strip", {"size": "2147483647"}), "card", {"type": "title"})
    S(S(S(cards, "edge", {"name": "bottom"}), "strip", {"size": "200"}), "card", {"type": "caption"})
    if colour_by:
        S(S(S(cards, "edge", {"name": "right"}), "strip", {"size": "160"}), "card", {"pane-specification-id": "0", "param": f"[{ds}].{colour_by}", "type": "color"})
    explain = S(wb, "explain-data", {"enabled-for-viewer": "true", "extreme-values-enabled-for-all": "true"})
    S(explain, "explanation-types")
    ET.indent(wb, "  ")
    return "<?xml version='1.0' encoding='utf-8' ?>\n" + ET.tostring(wb, encoding="unicode")


def export_columns(spec, rows):
    """Readable column labels for an export, and the plotted rows re-keyed to those labels."""
    used = set()
    x_col = pbi_label(spec.get("x_label") or spec["x"], used)
    y_col = pbi_label(spec.get("y_label") or spec["y"], used)
    series_col = pbi_label(spec["series"], used) if spec.get("series") and any(spec["series"] in r for r in rows) else None
    n_col = pbi_label(spec["denominator"], used) if spec.get("denominator") and any(spec["denominator"] in r for r in rows) else None
    keyed = []
    for r in rows:
        item = {x_col: str(r.get(spec["x"])), y_col: r.get(spec["y"])}
        if series_col:
            item[series_col] = str(r.get(spec["series"], ""))
        if n_col:
            item[n_col] = r.get(spec["denominator"])
        keyed.append(item)
    return x_col, y_col, series_col, n_col, keyed


@app.get("/api/runs/{run_id}/charts/{source_id}/tableau.twbx")
def chart_tableau(run_id: str, source_id: str):
    """A Tableau packaged workbook that opens on this chart, with its description in the caption."""
    import zipfile
    spec, artifact, info, team, rows = export_context(run_id, source_id)
    x_col, y_col, series_col, n_col, keyed = export_columns(spec, rows)
    bar = spec.get("kind") == "bar"
    title = spec.get("title") or "Echo chart"
    sections, footer = chart_story(spec, artifact, info, x_col, y_col, series_col, bar)
    subtitle = f"{team} · manager {info.get('manager_id')} · {info.get('start_date')} to {info.get('end_date')} · exported from Echo on {date.today().isoformat()}"
    columns = [x_col] + ([series_col] if series_col else []) + [y_col] + ([n_col] if n_col else [])
    data = io.StringIO()
    writer = csv.writer(data, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows([[r.get(c) for c in columns] for r in keyed])
    workbook = tableau_twb(title, subtitle, sections + [("Note", [footer], False)], x_col, y_col, series_col, n_col, keyed, bar, PBI_PALETTE)
    name = export_name(title)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{name}.twb", workbook.encode("utf-8"))
        archive.writestr("Data/Datafiles/chart.csv", data.getvalue().encode("utf-8"))
    return Response(buffer.getvalue(), media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{name}.twbx"'})


# ---------- Excel workbook export ----------
# A sheet with the title, a native Excel chart in Echo's pastels and the description, plus a Numbers sheet.
# Needs openpyxl in the backend's Python (listed in requirements.txt).

@app.get("/api/runs/{run_id}/charts/{source_id}/excel.xlsx")
def chart_excel(run_id: str, source_id: str):
    """An Excel workbook with this chart as a real Excel chart, its description and the numbers behind it."""
    try:
        from openpyxl import Workbook
        from openpyxl.chart import BarChart, LineChart, Reference
        from openpyxl.chart.marker import Marker
        from openpyxl.chart.series import DataPoint
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        raise HTTPException(503, "Excel export needs the openpyxl package. In Echo_UI\\backend run: "
                                 "..\\..\\Agent_Echo\\.venv\\Scripts\\python.exe -m pip install openpyxl, then restart the backend.")
    spec, artifact, info, team, rows = export_context(run_id, source_id)
    x_col, y_col, series_col, n_col, keyed = export_columns(spec, rows)
    bar = spec.get("kind") == "bar"
    title = spec.get("title") or "Echo chart"
    sections, footer = chart_story(spec, artifact, info, x_col, y_col, series_col, bar)
    ink, muted, sage, line = "1E2630", "526174", "E9EDDF", "C9D2DE"

    wb = Workbook()
    ws = wb.active
    ws.title = "Echo chart"
    ws.sheet_view.showGridLines = False
    ws["A1"] = title
    ws["A1"].font = Font(name="Calibri", size=18, bold=True, color=ink)
    ws["A2"] = f"{team} · manager {info.get('manager_id')} · {info.get('start_date')} to {info.get('end_date')} · exported from Echo on {date.today().isoformat()}"
    ws["A2"].font = Font(size=10, color=muted)

    # The numbers: one row per category; with a series, one column per series (the shape Excel charts need).
    categories = list(dict.fromkeys(r[x_col] for r in keyed))
    if series_col:
        names = list(dict.fromkeys(r[series_col] for r in keyed))
        header = [x_col] + names
        values = {(r[x_col], r[series_col]): r[y_col] for r in keyed}
        table = [[c] + [values.get((c, n)) for n in names] for c in categories]
    else:
        header = [x_col, y_col] + ([n_col] if n_col else [])
        table = [[r[x_col], r[y_col]] + ([r.get(n_col)] if n_col else []) for r in keyed]
    # The numbers get their own sheet, so the description's row heights never stretch the table.
    data = wb.create_sheet("Numbers")
    data.sheet_view.showGridLines = False
    thin = Side(style="thin", color=line)
    for j, text in enumerate(header, start=1):
        cell = data.cell(row=1, column=j, value=text)
        cell.font = Font(bold=True, color=ink)
        cell.fill = PatternFill("solid", fgColor=sage)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = Border(bottom=thin)
    for i, values_row in enumerate(table, start=2):
        for j, value in enumerate(values_row, start=1):
            cell = data.cell(row=i, column=j, value=value)
            cell.border = Border(bottom=thin)
            if j > 1 and isinstance(value, (int, float)):
                cell.number_format = "#,##0" if (n_col and header[j - 1] == n_col) else "#,##0.##"
    data.column_dimensions["A"].width = max(14, min(28, max(len(str(c)) for c in [x_col] + categories) + 2))
    for j in range(2, len(header) + 1):
        data.column_dimensions[data.cell(row=1, column=j).column_letter].width = max(12, min(22, len(str(header[j - 1])) + 2))
    data.freeze_panes = "A2"

    # The chart, in the same pastels as Echo.
    chart = BarChart() if bar else LineChart()
    if bar:
        chart.type, chart.gapWidth = "col", 60
    chart.title = f"{y_col} by {x_col}"
    chart.y_axis.title, chart.x_axis.title = y_col, x_col
    chart.y_axis.majorGridlines = None
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.x_axis.tickLblPos = "low"  # labels stay at the bottom even when bars go below zero
    count = len(header) - 1 if series_col else 1
    chart.add_data(Reference(data, min_col=2, max_col=1 + count, min_row=1, max_row=1 + len(table)), titles_from_data=True)
    chart.set_categories(Reference(data, min_col=1, min_row=2, max_row=1 + len(table)))
    for k, s in enumerate(chart.series):
        colour = PBI_PALETTE[k % len(PBI_PALETTE)].lstrip("#")
        if bar:
            s.graphicalProperties.solidFill = colour
            s.graphicalProperties.line.solidFill = colour
            if not series_col:  # a single series gets one pastel per bar, as on screen
                for p in range(len(table)):
                    point = DataPoint(idx=p)
                    point.graphicalProperties.solidFill = PBI_PALETTE[p % len(PBI_PALETTE)].lstrip("#")
                    point.graphicalProperties.line.solidFill = PBI_PALETTE[p % len(PBI_PALETTE)].lstrip("#")
                    s.dPt.append(point)
        else:
            s.graphicalProperties.line.solidFill = colour
            s.graphicalProperties.line.width = 28000
            s.marker = Marker(symbol="circle", size=7)
            s.marker.graphicalProperties.solidFill = colour
            s.marker.graphicalProperties.line.solidFill = "FFFFFF"
            s.smooth = False
    if not series_col:
        chart.legend = None
    chart.width, chart.height = 22, 10
    ws.add_chart(chart, "A4")

    # The description, under the chart and across the same width.
    span = 12
    for j in range(1, span + 1):
        ws.column_dimensions[ws.cell(row=1, column=j).column_letter].width = 10
    row = 25
    for heading, lines, bullets in sections + [("", [footer + " The numbers are on the Numbers sheet."], False)]:
        if heading:
            cell = ws.cell(row=row, column=1, value=heading)
            cell.font = Font(bold=True, size=11, color=ink)
            row += 1
        for text in lines:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
            cell = ws.cell(row=row, column=1, value=("• " if bullets else "") + text)
            cell.font = Font(size=10, color=muted, italic=not heading)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[row].height = 14 * max(1, -(-len(text) // 140))
            row += 1
        row += 1
    # Prints on one landscape page.
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 1
    wb.properties.title = title
    wb.properties.creator = "Echo"

    buffer = io.BytesIO()
    wb.save(buffer)
    return Response(buffer.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{export_name(title)}.xlsx"'})


# ---------- Presentation export (PowerPoint) ----------
# The manager view's "Present" tab shows an investigation as slides; this builds the same deck as an
# editable .pptx with native charts. Needs python-pptx (in requirements.txt). Content comes only from the
# runs' manager projections (no survey comment text) and is limited to the manager who asked.

PPT_INK, PPT_MUTED, PPT_SAGE, PPT_SAGE_DARK = "1E2630", "556477", "63703C", "515C30"
PPT_PAPER, PPT_LINE, PPT_DARK1, PPT_DARK2, PPT_PALE = "FBFBF7", "E3E8EE", "2C3A27", "1F2834", "C8D3A8"
CITE = re.compile(r"\s*\[[A-Za-z]+\d*(?::[A-Za-z0-9_-]+)?\]")


def _clean(text):
    return CITE.sub("", str(text or "")).strip()


def _mix(colour, weight, base="FFFFFF"):
    """colour blended into base: weight 0..1 of colour."""
    c = [int(colour.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(base[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(c[i] * weight + b[i] * (1 - weight)):02X}" for i in range(3))


def build_presentation(manager, results):
    """results: [(question, meta, artifact or None)]. Returns .pptx bytes."""
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_LABEL_POSITION
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    blank = deck.slide_layouts[6]
    rgb = lambda h: RGBColor.from_string(h.lstrip("#").upper())
    palette = [c.lstrip("#") for c in PBI_PALETTE]
    team = manager.get("Primary_Team") or manager.get("Manager_ID")
    serif, sans = "Georgia", "Segoe UI"

    def box(slide, x, y, w, h, fill=None, line=None, radius=None, shape=None):
        kind = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE)
        sh = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        if radius and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = radius
        if fill:
            sh.fill.solid()
            sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line)
            sh.line.width = Pt(0.75)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    def text(slide, x, y, w, h, runs_or_text, size=16, colour=PPT_INK, font=sans, bold=False, align=None, anchor=MSO_ANCHOR.TOP, spacing=None):
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        paragraphs = runs_or_text if isinstance(runs_or_text, list) else [runs_or_text]
        for i, para in enumerate(paragraphs):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            if align:
                p.alignment = align
            if spacing:
                p.space_after = Pt(spacing)
            r = p.add_run()
            r.text = para
            r.font.size, r.font.name, r.font.bold = Pt(size), font, bold
            r.font.color.rgb = rgb(colour)
        return tb

    def bullets(slide, x, y, w, h, items, dot, size=16, numbered=False, colour=PPT_INK):
        top = y
        per_line = max(20, int(w * 72 / (size * 0.52)))  # rough characters per line at this size
        for i, item in enumerate(items):
            lines = max(1, -(-len(item) // per_line))
            height = lines * size * 1.32 / 72
            if top + height > y + h + 0.05:
                break
            if numbered:
                b = box(slide, x, top + 0.02, 0.32, 0.32, fill=dot, shape=MSO_SHAPE.OVAL)
                tf = b.text_frame
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                r = p.add_run()
                r.text = str(i + 1)
                r.font.size, r.font.bold, r.font.name = Pt(12), True, sans
                r.font.color.rgb = rgb("FFFFFF")
                indent = 0.48
            else:
                box(slide, x + 0.02, top + size / 72 * 0.42, 0.11, 0.11, fill=dot, shape=MSO_SHAPE.OVAL)
                indent = 0.3
            text(slide, x + indent, top, w - indent, height, item, size=size, colour=colour)
            top += height + 0.16
        return top

    def ripples(slide, cx, cy, step=0):
        for i, r in enumerate((0.85, 1.6, 2.45, 3.35, 4.3, 5.35)):
            o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - r), Inches(cy - r), Inches(2 * r), Inches(2 * r))
            o.fill.background()
            o.line.color.rgb = rgb(_mix(PPT_PALE, 0.55 - i * 0.075, "2A3530"))
            o.line.width = Pt(1.4 if i == 0 else 0.9)
            o.shadow.inherit = False

    def dark_background(slide):
        bg = box(slide, 0, 0, 13.333, 7.5, fill=PPT_DARK1)
        bg.fill.gradient()
        bg.fill.gradient_angle = 35
        stops = bg.fill.gradient_stops
        stops[0].color.rgb, stops[0].position = rgb("34432E"), 0
        stops[1].color.rgb, stops[1].position = rgb(PPT_DARK2), 1.0

    def content(eyebrow, page, total):
        slide = deck.slides.add_slide(blank)
        box(slide, 0, 0, 13.333, 7.5, fill=PPT_PAPER)
        ribbon = box(slide, 0, 0, 13.333, 0.07, fill="A8B58A")
        ribbon.fill.gradient()
        ribbon.fill.gradient_angle = 0
        st = ribbon.fill.gradient_stops
        st[0].color.rgb, st[1].color.rgb = rgb("A8B58A"), rgb("E8B4BC")
        text(slide, 0.67, 0.42, 9, 0.3, eyebrow.upper(), size=11, colour=PPT_SAGE, bold=True)
        text(slide, 0.67, 6.95, 8, 0.25, f"Echo · {team}", size=10, colour="6F8095")
        text(slide, 11.0, 6.95, 1.67, 0.25, f"{page} / {total}", size=10, colour="6F8095", align=PP_ALIGN.RIGHT)
        return slide

    def title(slide, words, size=30, top=0.8):
        text(slide, 0.67, top, 12.0, 1.0, words, size=size, font=serif, bold=True)

    # Which slides there will be, so pages can be numbered.
    answered = [(q, m, a) for q, m, a in results if a and a.get("status") == "complete"]
    plan = ["cover"] + (["agenda"] if len(results) > 1 else [])
    for i, (q, m, a) in enumerate(results):
        plan.append(("result", i))
        if a and a.get("status") == "complete" and (a.get("impact") or a.get("next_steps") or a.get("watch")):
            plan.append(("sowhat", i))
    actions = [(q, _clean((a.get("next_steps") or [""])[0])) for q, m, a in answered if (a.get("next_steps") or [""])[0]]
    if len(actions) > 1:
        plan.append("actions")
    plan.append("close")
    total = len(plan)
    first_meta = next((m for _, m, _ in results if m), {}) or {}
    period = f"{first_meta.get('start_date')} to {first_meta.get('end_date')}" if first_meta.get("start_date") else ""

    for page, item in enumerate(plan, start=1):
        if item == "cover":
            slide = deck.slides.add_slide(blank)
            dark_background(slide)
            ripples(slide, 12.3, 0.9)
            text(slide, 0.85, 0.75, 6, 0.4, "Echo · team briefing", size=14, colour=PPT_PALE)
            text(slide, 0.85, 3.55, 8.6, 1.1, team, size=54, colour="FFFFFF", font=serif, bold=True)
            text(slide, 0.85, 4.75, 8.6, 0.9, _clean(results[0][0]) if results else "", size=22, colour="E4E8E0", font=serif)
            meta_line = "     ".join(x for x in (f"Prepared for {manager.get('Manager_Name')}", date.today().strftime("%B %d, %Y").replace(" 0", " "),
                                                    f"Data: {period}" if period else "", f"{len(results)} question{'s' if len(results) != 1 else ''} investigated") if x)
            text(slide, 0.85, 5.95, 11.5, 0.4, meta_line, size=13, colour=PPT_PALE)
            continue
        if item == "agenda":
            slide = content("What we looked at", page, total)
            title(slide, f"{len(results)} questions, one story", size=36)
            for i, (q, _, _) in enumerate(results[:8]):
                col, row = i % 2, i // 2
                x, y = 0.67 + col * 6.15, 2.0 + row * 1.12
                box(slide, x, y, 5.85, 0.92, fill="FFFFFF", line=PPT_LINE, radius=0.18)
                b = box(slide, x + 0.22, y + 0.21, 0.5, 0.5, fill=palette[i % len(palette)], shape=MSO_SHAPE.OVAL)
                tf = b.text_frame
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                r = p.add_run()
                r.text, r.font.size, r.font.bold, r.font.name = str(i + 1), Pt(16), True, serif
                r.font.color.rgb = rgb("FFFFFF")
                text(slide, x + 0.9, y + 0.12, 4.75, 0.7, q, size=16, anchor=MSO_ANCHOR.MIDDLE)
            continue
        if item == "actions":
            slide = content("Putting it together", page, total)
            title(slide, "Actions for this quarter", size=36)
            y = 1.95
            for i, (q, step) in enumerate(actions[:5]):
                colour = palette[[r[0] for r in results].index(q) % len(palette)]
                long = len(step) > 95
                box(slide, 0.67, y, 12.0, 1.0 if long else 0.86, fill="FFFFFF", line=PPT_LINE, radius=0.15)
                b = box(slide, 0.9, y + (0.25 if long else 0.18), 0.5, 0.5, fill=colour, shape=MSO_SHAPE.OVAL)
                p = b.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                b.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
                r = p.add_run()
                r.text, r.font.size, r.font.bold, r.font.name = str(i + 1), Pt(16), True, serif
                r.font.color.rgb = rgb("FFFFFF")
                text(slide, 1.65, y + 0.1, 10.8, 0.6 if long else 0.4, step, size=14 if long else 15)
                text(slide, 1.65, y + (0.68 if long else 0.52), 10.8, 0.3, f"From: {q}", size=11, colour="6F8095")
                y += 1.12 if long else 0.98
            continue
        if item == "close":
            slide = deck.slides.add_slide(blank)
            dark_background(slide)
            ripples(slide, 0.9, 7.1)
            checked = sum(1 for _, _, a in results if a and (a.get("verification") or {}).get("decision") == "accept" and a.get("status") == "complete")
            text(slide, 4.4, 1.3, 8.2, 0.4, "HOW THIS WAS CHECKED", size=13, colour=PPT_PALE, bold=True)
            text(slide, 4.4, 1.8, 8.4, 1.3, f"{checked} of {len(results)} result{'s' if len(results) != 1 else ''} passed Echo's fact-check",
                 size=34, colour="FFFFFF", font=serif, bold=True)
            facts = [f"Only {team}'s records and survey scores{', ' + period if period else ''}.",
                     "Every number comes from a query that was re-run before release.",
                     "Team-level results only: no individual survey responses are shown."]
            bullets(slide, 4.4, 3.45, 8.2, 2.0, facts, PPT_PALE, size=16, colour="E4E8E0")
            text(slide, 4.4, 5.6, 8.2, 0.4, "Echo supports human review. It is not for personnel decisions.", size=12, colour=PPT_PALE)
            continue

        kind, i = item
        q, meta, a = results[i]
        colour = palette[i % len(palette)]
        eyebrow = f"Question {i + 1} of {len(results)}" if len(results) > 1 else "The question"
        if kind == "result":
            slide = content(eyebrow, page, total)
            title(slide, q, size=28 if len(q) < 70 else 24)
            if not a or a.get("status") not in ("complete", "declined"):
                text(slide, 0.67, 2.2, 12, 0.6, "This question did not finish, so it has no result to present.", size=18, colour=PPT_MUTED)
                continue
            if a.get("status") == "declined":
                box(slide, 0.67, 2.2, 12, 2.6, fill="FFF1F2", line="FECDD3", radius=0.08)
                text(slide, 1.0, 2.45, 11.3, 0.5, "Echo declined this request", size=20, colour="9F1239", bold=True)
                text(slide, 1.0, 3.05, 11.3, 1.6, _clean(a.get("answer")), size=16, colour="3C4655")
                continue
            findings = [_clean(f.get("text")) for f in a.get("findings") or [] if f.get("status", "supported") == "supported"]
            lead = findings[0] if findings else _clean(a.get("answer")).split(". ")[0]
            rest = findings[1:4]
            spec = ((a.get("visualization") or {}).get("charts") or [None])[0]
            evidence = list(a.get("evidence") or []) + [e for d in a.get("delegations") or [] for e in d.get("evidence") or []]
            source = next((e for e in evidence if spec and e.get("citation_id") == spec.get("source_id") and isinstance(e.get("sql"), str)), None)
            rows = [r for r in (source or {}).get("rows") or [] if spec and r.get(spec["y"]) is not None]
            has_chart = bool(spec and rows)
            left_w = 4.95 if has_chart else 12.0
            card = box(slide, 0.67, 1.85, left_w, 2.05 if has_chart else 1.6, fill=_mix(colour, 0.16), radius=0.08)
            text(slide, 0.95, 2.05, left_w - 0.55, 0.3, "THE HEADLINE", size=10, colour=_mix(colour, 0.7, PPT_INK), bold=True)
            lead_size = 18 if len(lead) < 150 else 15
            text(slide, 0.95, 2.38, left_w - 0.55, 1.45, lead, size=lead_size, font=serif)
            if rest:
                bullets(slide, 0.67, 4.15 if has_chart else 3.7, left_w, 2.2 if has_chart else 2.6, rest, colour, size=14 if has_chart else 16)
            verified = (a.get("verification") or {}).get("decision") == "accept"
            text(slide, 0.67, 6.45, left_w, 0.3, ("✓ Checked by ZeroSugar, Echo's fact-checker" if verified else "Not fully verified: read with care"), size=11, colour=PPT_MUTED)
            if has_chart:
                box(slide, 5.95, 1.85, 6.72, 4.85, fill="FFFFFF", line=PPT_LINE, radius=0.05)
                text(slide, 6.2, 2.0, 6.2, 0.35, spec.get("title") or "", size=13, bold=True)
                x_col, y_col, series_col, _, keyed = export_columns(spec, rows)
                categories = list(dict.fromkeys(r[x_col] for r in keyed))
                data = CategoryChartData()
                data.categories = categories
                names = list(dict.fromkeys(r[series_col] for r in keyed)) if series_col else [y_col]
                for name in names:
                    values = {r[x_col]: r[y_col] for r in keyed if not series_col or r[series_col] == name}
                    data.add_series(str(name), [float(values[c]) if values.get(c) is not None else None for c in categories])
                bar = spec.get("kind") == "bar"
                frame = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED if bar else XL_CHART_TYPE.LINE_MARKERS,
                                               Inches(6.1), Inches(2.4), Inches(6.45), Inches(4.15), data)
                chart = frame.chart
                chart.has_title = False  # the card above the chart already carries its title
                chart.font.size, chart.font.name = Pt(10), sans
                chart.font.color.rgb = rgb(PPT_MUTED)
                chart.has_legend = len(names) > 1
                if chart.has_legend:
                    chart.legend.position, chart.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
                va, ca = chart.value_axis, chart.category_axis
                va.has_major_gridlines = True
                va.major_gridlines.format.line.color.rgb = rgb("E8ECF0")
                va.format.line.fill.background()
                ca.format.line.color.rgb = rgb("D5DCE4")
                ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
                ca.has_title = va.has_title = True
                ca.axis_title.text_frame.text, va.axis_title.text_frame.text = x_col, y_col
                for t in (ca.axis_title, va.axis_title):
                    for r in t.text_frame.paragraphs[0].runs:
                        r.font.size, r.font.bold = Pt(10), False
                        r.font.color.rgb = rgb(PPT_MUTED)
                plot = chart.plots[0]
                if bar:
                    plot.gap_width = 60
                for k, series in enumerate(plot.series):
                    c = palette[k % len(palette)]
                    if bar:
                        series.format.fill.solid()
                        series.format.fill.fore_color.rgb = rgb(c)
                        if len(names) == 1:  # one pastel per bar, as on screen
                            for p in range(len(categories)):
                                point = series.points[p]
                                point.format.fill.solid()
                                point.format.fill.fore_color.rgb = rgb(palette[p % len(palette)])
                    else:
                        series.format.line.color.rgb = rgb(c)
                        series.format.line.width = Pt(2.5)
                        series.smooth = False
                        series.marker.style, series.marker.size = XL_MARKER_STYLE.CIRCLE, 8
                        series.marker.format.fill.solid()
                        series.marker.format.fill.fore_color.rgb = rgb(c)
                        series.marker.format.line.color.rgb = rgb("FFFFFF")
            continue

        # "So what": why it matters, what to do first, what to watch.
        slide = content(f"{eyebrow} · so what", page, total)
        title(slide, "What it means, and what to do")
        impact = [_clean(t) for t in (a.get("impact") or [])[:3]]
        steps = [_clean(t) for t in (a.get("next_steps") or [])[:3]]
        watch = (a.get("watch") or [])[:3]
        caution = _clean((a.get("limitations") or [""])[0])
        bottom = 5.05 if (watch or caution) else 6.55
        cards = [c for c in (("Why it matters", impact, "FFF8E8", "F3DFA9", "92400E", "D9A24A", False),
                             ("What to do first", steps, "F1F4E8", "D6DCC4", PPT_SAGE_DARK, "7B934B", True)) if c[1]]
        width = (12.0 - 0.3 * (len(cards) - 1)) / max(1, len(cards))
        for k, (heading, items, fill, line, ink, dot, numbered) in enumerate(cards):
            x = 0.67 + k * (width + 0.3)
            box(slide, x, 1.7, width, bottom - 1.7, fill=fill, line=line, radius=0.07)
            text(slide, x + 0.3, 1.92, width - 0.6, 0.35, heading, size=14, colour=ink, bold=True)
            length = sum(len(t) for t in items)
            bullets(slide, x + 0.3, 2.4, width - 0.6, bottom - 2.55, items, dot, size=14 if length > 380 else 15, numbered=numbered)
        if watch or caution:
            tiles = len(watch)
            avail = 12.0 - (3.6 if caution else 0)
            tile_w = (avail - 0.2 * max(0, tiles - 1)) / max(1, tiles) if tiles else 0
            for k, w in enumerate(watch):
                x = 0.67 + k * (tile_w + 0.2)
                box(slide, x, 5.3, tile_w, 1.25, fill="FFFFFF", line=PPT_LINE, radius=0.1)
                text(slide, x + 0.2, 5.42, tile_w - 0.4, 0.25, "WATCH NEXT QUARTER", size=9, colour="6F8095", bold=True)
                text(slide, x + 0.2, 5.66, tile_w - 0.4, 0.5, w.get("metric", ""), size=12, bold=True)
                text(slide, x + 0.2, 6.15, tile_w - 0.4, 0.3, f"now {w.get('baseline')} · aim {w.get('goal')}", size=11, colour=PPT_MUTED)
            if caution:
                x = 0.67 + (avail + 0.2 if tiles else 0)
                text(slide, x, 5.35, 12.67 - x, 1.2, "Before you act: " + caution, size=11, colour="6F8095", anchor=MSO_ANCHOR.MIDDLE)

    deck.core_properties.title = f"Echo briefing · {team}"
    deck.core_properties.author = "Echo"
    buffer = io.BytesIO()
    deck.save(buffer)
    return buffer.getvalue()


@app.get("/api/presentation.pptx")
def presentation(manager_id: str, runs: str):
    """An investigation's results as an editable PowerPoint deck (the same slides as the Present tab)."""
    try:
        import pptx  # noqa: F401
    except ImportError:
        raise HTTPException(503, "PowerPoint download needs the python-pptx package. In Echo_UI\\backend run: "
                                 "..\\..\\Agent_Echo\\.venv\\Scripts\\python.exe -m pip install python-pptx, then restart the backend.")
    ids = [r for r in runs.split(",") if r][:20]
    if not ids:
        raise HTTPException(400, "No results to present.")
    with database() as db:
        row = db.execute("SELECT Manager_ID, Manager_Name, Primary_Team FROM HR_managers WHERE Manager_ID = ?", (manager_id.upper(),)).fetchone()
    if row is None:
        raise HTTPException(404, "Unknown manager.")
    manager = dict(row)
    results = []
    for run_id in ids:
        path = run_dir(run_id)
        info = summarize(run_id)
        if (info.get("manager_id") or "").upper() != manager["Manager_ID"]:
            raise HTTPException(404, "That result belongs to a different manager.")
        artifact = read_json(path / "artifact.json")
        results.append((info.get("question") or "", info, without_comment_text(artifact) if artifact else None))
    name = safe_filename(f"Echo briefing - {manager['Primary_Team']}") + ".pptx"
    return Response(build_presentation(manager, results), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


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
