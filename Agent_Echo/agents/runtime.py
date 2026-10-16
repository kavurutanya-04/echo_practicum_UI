"""Bounded model/tool loop shared by the two independently configured specialists."""

from dataclasses import dataclass, field
import json
import re
import time
import hashlib
from .execution_log import record, error_summary
from .findings import normalize_citations


def function_tool(name, description, properties):
    return {"type": "function", "name": name, "description": description,
            "strict": True, "parameters": {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}}


def reject_calls(history, turn, message):
    """Answer every outstanding tool call before asking a provider to repair it."""
    if turn.calls:
        for call in turn.calls:
            history.append({"type": "function_call_output", "call_id": call.call_id,
                            "output": json.dumps({"error": message})})
    else:
        history.append({"role": "user", "content": message})


@dataclass
class AgentResult:
    agent: str
    question: str
    answer: str
    scope: dict
    evidence: list = field(default_factory=list)
    tool_trace: list = field(default_factory=list)
    mode: str = "live"
    verification: dict = field(default_factory=dict)
    delegations: list = field(default_factory=list)
    connections: dict = field(default_factory=dict)
    visualization: dict = field(default_factory=dict)
    rag: dict = field(default_factory=dict)
    execution: dict = field(default_factory=dict)
    sentiment: dict = field(default_factory=dict)
    status: str = "unverified"
    findings: list = field(default_factory=list)
    limitations: list = field(default_factory=list)
    next_steps: list = field(default_factory=list)
    clarification_questions: list = field(default_factory=list)
    failure: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)


class AgentRunError(RuntimeError):
    """Keep intermediate evidence separate from released, reviewed findings."""
    def __init__(self, message, result):
        super().__init__(message)
        self.result = result


class RunBudget:
    """One shared limit across coordination, specialist calls and verification."""

    def __init__(self, model_limit=32, tool_limit=48, seconds=300, embedding_limit=256):
        self.model_limit, self.tool_limit = model_limit, tool_limit
        self.models, self.tools = 0, 0
        self.embedding_limit, self.embeddings = embedding_limit, 0
        self.deadline = time.monotonic() + seconds

    def consume(self, kind):
        if time.monotonic() > self.deadline:
            raise RuntimeError("Workflow elapsed-time budget exceeded.")
        if kind == "model":
            self.models += 1
            exceeded = self.models > self.model_limit
        elif kind == "tool":
            self.tools += 1
            exceeded = self.tools > self.tool_limit
        elif kind == "embedding":
            self.embeddings += 1
            exceeded = self.embeddings > self.embedding_limit
        else:
            raise ValueError("Unknown budget category.")
        if exceeded:
            raise RuntimeError("Workflow call budget exceeded.")

    def remaining(self):
        return {"model_calls": max(0, self.model_limit-self.models),
                "tool_calls": max(0, self.tool_limit-self.tools),
                "seconds": round(max(0, self.deadline-time.monotonic()), 2)}


class Specialist:
    def __init__(self, name, instructions, model, scope, definitions, handlers, mode="live", budget=None):
        self.name, self.instructions, self.model = name, instructions, model
        self.scope, self.definitions, self.handlers, self.mode = scope, definitions, handlers, mode
        self.budget = budget

    def run(self, question, initial_evidence=(), context=()):
        self.last_result = AgentResult(self.name, question, "", self.scope.__dict__, mode=self.mode, status="failed")
        try:
            return self._run(question, initial_evidence, context)
        except RuntimeError as error:
            self.last_result.failure = error_summary(error)
            record("agent_failed", agent=self.name, **self.last_result.failure)
            raise AgentRunError(str(error), self.last_result) from None

    def _run(self, question, initial_evidence=(), context=()):
        record("agent_started", agent=self.name)
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("Question must contain 1 to 4,000 characters.")
        history = [{"role": "user", "content": question}]
        history.extend(context)
        evidence, trace = list(initial_evidence), []
        self.last_result.evidence, self.last_result.tool_trace = evidence, trace
        known = {item["citation_id"] for item in evidence}
        budget = self.budget or RunBudget()
        instructions = self.instructions + "\nTrusted application scope: " + json.dumps(self.scope.__dict__)
        last_action = "no completed turn"
        cache, close_next = {}, False
        for step in range(7):
            closing = step == 6 or close_next or len(trace) >= 10 or budget.remaining()["model_calls"] <= (2 if self.name == "Original" else 3)
            record("agent_turn", agent=self.name, turn=step + 1, closing=closing, remaining=budget.remaining())
            budget.consume("model")
            turn_instructions = instructions + f"\nYou have {7-step} turns remaining, including your final answer."
            if closing:
                record("agent_closing", agent=self.name, reason="repeat_or_budget_or_final_turn")
                turn_instructions += ("\nThis is your closing turn. No tools are available. Answer in English using "
                    "only existing evidence IDs, or explain exactly which requested results could not be established. "
                    "Do not invent numbers or treat incomplete evidence as a complete answer.")
            turn = self.model.respond(turn_instructions, history, [] if closing else self.definitions,
                                      require_tool=bool(not closing and self.definitions and step == 0 and not initial_evidence))
            history.extend(turn.output_items)
            if closing and turn.calls:
                break
            if not turn.calls:
                if not turn.text.strip():
                    raise RuntimeError("The agent returned no answer.")
                self.last_result.diagnostics = {"last_unverified_text": turn.text}
                normalized = normalize_citations(turn.text, known)
                if normalized != turn.text:
                    record("citations_normalized", agent=self.name)
                    turn.text = normalized
                cited = set(re.findall(r"\[([A-Za-z0-9_:-]+)\]", turn.text))
                unknown = cited - known
                if unknown or (evidence and not (cited & known)):
                    last_action = "repairing missing or unknown evidence citations"
                    record("citation_repair", agent=self.name, unknown_citations=len(unknown),
                           cited_count=len(cited), known_count=len(known),
                           missing_evidence_citation=bool(evidence and not (cited & known)))
                    history.append({"role": "user", "content":
                        "Repair citation formatting. Use only evidence IDs returned by your tools in square brackets. "
                        "Ground findings in those sources; do not fabricate citations. Available IDs: " + ", ".join(sorted(known))})
                    continue
                record("agent_finished", agent=self.name, evidence_count=len(evidence))
                return AgentResult(self.name, question, turn.text, self.scope.__dict__, evidence, trace, self.mode)
            if len(turn.calls) > 4 or len(trace) + len(turn.calls) > 12:
                raise RuntimeError(f"{self.name} agent tool-call budget exceeded; no unverified answer was returned.")
            last_action = "calling tools: " + ", ".join(
                call.name if call.name in self.handlers else "unavailable tool" for call in turn.calls)
            tool_errors = 0
            for call in turn.calls:
                fingerprint = None
                tool_name = call.name if call.name in self.handlers else "unavailable_tool"
                record("tool_started", agent=self.name, tool=tool_name)
                try:
                    if call.name not in self.handlers:
                        raise ValueError("Tool is not available to this agent.")
                    arguments = json.loads(call.arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be an object.")
                    declared = next((t for t in self.definitions if t["name"] == call.name), None)
                    if declared and "parameters" in declared:
                        allowed = set(declared["parameters"]["properties"])
                        if set(arguments)-allowed:
                            raise ValueError("Tool arguments do not match its declared schema. Allowed names: " + ", ".join(sorted(allowed)))
                    fingerprint = hashlib.sha256((call.name+json.dumps(arguments, sort_keys=True)).encode()).hexdigest()[:20]
                    record("tool_request", agent=self.name, tool=tool_name, request_fingerprint=fingerprint,
                           remaining=budget.remaining())
                    if fingerprint in cache:
                        result = cache[fingerprint]
                        close_next = True
                        record("tool_cache_hit", agent=self.name, tool=tool_name, request_fingerprint=fingerprint)
                    else:
                        budget.consume("tool")
                        result = self.handlers[call.name](**arguments)
                        cache[fingerprint] = result
                    if len(json.dumps(result)) > 80_000:
                        raise ValueError("Result is too large. Select fewer columns or aggregate the query.")
                except (ValueError, TypeError) as error:
                    record("tool_validation_failed", agent=self.name, tool=tool_name, **error_summary(error))
                    result = {"error": str(error)}
                    if fingerprint is not None:
                        cache[fingerprint] = result
                except BaseException as error:
                    record("tool_failed", agent=self.name, tool=tool_name, **error_summary(error))
                    raise
                if "error" in result:
                    tool_errors += 1
                record("tool_finished", agent=self.name, tool=tool_name, success="error" not in result,
                       rows=len(result.get("rows", [])), passages=len(result.get("passages", [])),
                       truncated=bool(result.get("truncated", False)))
                trace.append({"tool": call.name, "arguments": call.arguments, "result": result})
                if "citation_id" in result and result["citation_id"] not in known:
                    evidence.append(result)
                    known.add(result["citation_id"])
                for passage in result.get("passages", []):
                    if passage["citation_id"] not in known:
                        evidence.append(passage)
                    known.add(passage["citation_id"])
                for item in result.get("evidence", []):
                    if item["citation_id"] not in known:
                        evidence.append(item)
                    known.add(item["citation_id"])
                history.append({"type": "function_call_output", "call_id": call.call_id,
                                "output": json.dumps(result, ensure_ascii=False)})
            if tool_errors:
                last_action += f" ({tool_errors} tool errors)"
        record("agent_turn_limit", agent=self.name, turns=step + 1)
        raise RuntimeError(f"{self.name} agent turn budget exceeded after {step + 1} model turns; "
                           f"last action: {last_action}. No unverified answer was returned.")
