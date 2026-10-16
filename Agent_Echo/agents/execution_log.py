"""Incremental local execution diagnostics, without prompts, records or credentials."""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
import uuid

_active = ContextVar("echo_execution_log", default=None)


def error_summary(error):
    """Classify errors without persisting arbitrary exception/provider text."""
    message = str(error).lower()
    category = "execution_error"
    for phrase, name in (
        ("turn budget", "agent_turn_limit"), ("tool-call budget", "agent_tool_limit"),
        ("elapsed-time budget", "time_limit"), ("call budget", "workflow_call_limit"),
        ("sentiment classification was incomplete", "incomplete_sentiment"),
        ("no such column", "sql_unknown_column"), ("no such table", "sql_unknown_table"),
        ("syntax error", "sql_syntax"), ("query rejected", "sql_rejected"),
        ("quote must be an exact", "invalid_source_quote"),
        ("cover every eligible comment", "incomplete_label_coverage"),
        ("timed out", "provider_timeout"), ("could not connect", "provider_connection"),
        ("missing profile configuration", "missing_configuration"),
        ("did not complete", "incomplete_model_response"),
    ):
        if phrase in message:
            category = name
            break
    result = {"error_type": type(error).__name__, "error_category": category}
    status = re.search(r"http ([1-5][0-9]{2})\b", message)
    if status:
        result.update(error_category="provider_http", http_status=int(status[1]))
    return result


def record(event, **fields):
    log = _active.get()
    if log is not None:
        log.write(event, **fields)


class RunLog:
    def __init__(self, directory, **metadata):
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:12]
        self.path = Path(directory).resolve() / (self.run_id + ".jsonl")
        self.metadata, self.exit_code = metadata, 1

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("x", encoding="utf-8")
        self.started = time.monotonic()
        self.token = _active.set(self)
        try:
            self.write("run_started", **self.metadata)
        except BaseException:
            _active.reset(self.token)
            self.stream.close()
            raise
        return self

    def write(self, event, **fields):
        entry = {"time_utc": datetime.now(timezone.utc).isoformat(), "run_id": self.run_id,
                 "elapsed_seconds": round(time.monotonic() - self.started, 3), "event": event, **fields}
        self.stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.stream.flush()

    def finish(self, exit_code):
        self.exit_code = exit_code

    def __exit__(self, kind, error, traceback):
        try:
            if error is not None:
                self.exit_code = 130 if isinstance(error, KeyboardInterrupt) else 1
                self.write("run_error", **error_summary(error))
            status = {0: "completed", 2: "revision_required", 130: "cancelled"}.get(self.exit_code, "failed")
            self.write("run_finished", status=status, exit_code=self.exit_code)
        finally:
            _active.reset(self.token)
            self.stream.close()


class LoggedModel:
    def __init__(self, model, agent, profile):
        self.wrapped, self.agent, self.profile = model, agent, profile

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    def respond(self, instructions, history, tools, require_tool=False):
        call_id = uuid.uuid4().hex[:12]
        details = {"agent": self.agent, "profile": self.profile, "call_id": call_id}
        record("model_started", **details, history_items=len(history), require_tool=require_tool)
        try:
            turn = self.wrapped.respond(instructions, history, tools, require_tool)
        except BaseException as error:
            record("model_failed", **details, **error_summary(error))
            raise
        allowed = {tool["name"] for tool in tools}
        record("model_finished", **details, answer_characters=len(turn.text),
               tools=[call.name if call.name in allowed else "unavailable_tool" for call in turn.calls])
        return turn


def logged_model(model, agent, profile):
    return LoggedModel(model, agent, profile) if _active.get() is not None else model
