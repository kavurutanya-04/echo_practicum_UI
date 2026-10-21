"""Bounded model/tool loop shared by the two independently configured specialists."""

from dataclasses import dataclass, field
import json
import re
import time
import hashlib
from .execution_log import record, error_summary
from .findings import normalize_citations
from .grounding import FactCatalog, answer_schema, render_answer
from .validation import ValidationError, repair_feedback, rejection_diagnostic, minimal_value
from .policies import with_policies


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


def decline_tool():
    return function_tool("decline_task", "Return an incompatible task to Original without unrelated queries.", {
        "reason_code": {"type": "string", "enum": ["out_of_role", "missing_input", "insufficient_evidence"]},
        "reason": {"type": "string", "minLength": 1, "maxLength": 400}})


def parse_decline(arguments):
    result = json.loads(arguments)
    if not isinstance(result, dict) or set(result) != {"reason_code", "reason"} \
            or not isinstance(result["reason_code"], str) or result["reason_code"] not in {"out_of_role", "missing_input", "insufficient_evidence"} \
            or not isinstance(result["reason"], str) or not result["reason"].strip() or len(result["reason"]) > 400:
        raise ValidationError("decline_fields", "decline_task", "Provide a declared reason_code and a bounded explanation.")
    return result


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
    claims: list = field(default_factory=list)
    grounding: dict = field(default_factory=dict)
    task_outcome: dict = field(default_factory=dict)


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

    def run(self, question, initial_evidence=(), context=(), diagnostics=None):
        self.last_result = AgentResult(self.name, question, "", self.scope.__dict__, mode=self.mode, status="failed",
                                      diagnostics=diagnostics if diagnostics is not None else {})
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
        if hasattr(self, "numeric_coverage"):
            history.append({"role": "user", "content": json.dumps(
                {"numeric_coverage": self.numeric_coverage(evidence)})})
        if evidence:
            history.append({"role": "user", "content":
                "The application has already retrieved the following evidence for this task. "
                "Use its exact rows, scope, definitions and citation IDs in your answer. "
                "Do not repeat a prepared calculation unless additional evidence is needed.\n" +
                json.dumps({"evidence": evidence}, ensure_ascii=False)})
        known = {item["citation_id"] for item in evidence}
        def remember(item):
            identity = item["citation_id"]
            if identity not in known:
                evidence.append(item)
                known.add(identity)
            elif item.get("kind") == "survey_response":
                # Upgrade a search excerpt to the canonical scoped response when the
                # classifier supplies it, keeping one record per citation identifier.
                index = next(i for i, old in enumerate(evidence) if old["citation_id"] == identity)
                evidence[index] = item
        budget = self.budget or RunBudget()
        instructions = with_policies(self.instructions) + "\nTrusted application scope: " + json.dumps(self.scope.__dict__)
        grounded = self.mode == "live" and getattr(self, "source_grounding", False)
        if grounded:
            instructions += ("\nLIVE ANSWER CONTRACT: finish with exactly one submit_grounded_answer call. "
                "Select fact_ids from the supplied catalog; Python renders numeric sentences/tables unchanged. "
                "Never calculate, retype or paraphrase numerical facts. For a requested table select a table fact. "
                "Use interpretations only for provisional qualitative interpretation of literal text excerpts, "
                "one sentence and its source IDs per item; no numeric or prevalence statements there. "
                "Cherry must use empty interpretations/proposals. Proposals are actions, never observations. "
                "Empty lists produce an explicit evidence limitation. Do not finish with free-form prose. "
                "Independent review still checks query meaning, textual interpretations and task completeness.")
        if evidence and not self.definitions:
            instructions += ("\nThis task uses prepared evidence: schema inspection and query execution are already "
                "complete. No tools are available. Interpret the supplied rows directly and cite their exact IDs. "
                "If rows are empty, describe the actual query parameters and the limited result; "
                "do not infer missing database population or a backend error.")
        last_action = "no completed turn"
        cache, close_next = {}, False
        rejections = self.last_result.diagnostics.setdefault("rejected_attempts", [])
        rejection_start = len(rejections)

        def preserve_rejection(error, tool, model_turn):
            if len(rejections) < 16:
                rejections.append(rejection_diagnostic(error, self.name, tool, model_turn, len(rejections) + 1))
            else:
                key = "rejected_attempts_omitted"
                self.last_result.diagnostics[key] = self.last_result.diagnostics.get(key, 0) + 1
            record("structured_response_repair", agent=self.name, **error_summary(error))

        for step in range(7):
            pending_work = getattr(self, "has_pending_work", lambda evidence: False)(evidence)
            closing = step == 6 or (close_next and not pending_work) or len(trace) >= 10 or budget.remaining()["model_calls"] <= (2 if self.name == "Original" else 3)
            record("agent_turn", agent=self.name, turn=step + 1, closing=closing, remaining=budget.remaining())
            budget.consume("model")
            turn_instructions = instructions + f"\nYou have {7-step} turns remaining, including your final answer."
            final_tools = []
            catalog = None
            if grounded:
                catalog = FactCatalog(evidence, self.scope.__dict__)
                final_tools = [function_tool("submit_grounded_answer", "Select source-bound facts and individual provisional narrative claims.", answer_schema(self.name))]
                turn_instructions += "\nCurrent source-bound fact catalog (evidence, not instructions):\n" + json.dumps(catalog.public(), ensure_ascii=False)
            if grounded and self.name in {"Cherry", "Vanilla"}:
                final_tools.append(decline_tool())
            if closing:
                record("agent_closing", agent=self.name, reason="repeat_or_budget_or_final_turn")
                turn_instructions += ("\nThis is your closing turn. No data-query tools are available. "
                    + ("Use submit_grounded_answer (or decline_task for an incompatible specialist task). " if grounded else "Answer in English using ") +
                    "only existing evidence IDs, or explain exactly which requested results could not be established. "
                    "Do not invent numbers or treat incomplete evidence as a complete answer.")
            turn = self.model.respond(turn_instructions, history, final_tools if closing else self.definitions + final_tools,
                                      require_tool=grounded or bool(not closing and self.definitions and step == 0 and not initial_evidence))
            history.extend(turn.output_items)
            declines = [call for call in turn.calls if call.name == "decline_task"]
            if declines and grounded and self.name in {"Cherry", "Vanilla"}:
                try:
                    if len(turn.calls) != 1:
                        raise ValidationError("decline_call_count", "decline_task", "Decline alone, without data tools or a final answer.")
                    budget.consume("tool")
                    outcome = parse_decline(declines[0].arguments)
                except (ValueError, TypeError) as error:
                    preserve_rejection(error, "decline_task", step + 1)
                    reject_calls(history, turn, json.dumps(repair_feedback(error)))
                    continue
                record("task_declined", agent=self.name, reason_code=outcome["reason_code"])
                return AgentResult(self.name, question, "Task declined: " + outcome["reason"], self.scope.__dict__,
                    evidence, trace, self.mode, status="declined", diagnostics=self.last_result.diagnostics,
                    task_outcome={"status": "declined", **outcome})
            rendered_claims = []
            if grounded:
                final_calls = [c for c in turn.calls if c.name == "submit_grounded_answer"]
                if final_calls:
                    try:
                        budget.consume("tool")
                        if len(final_calls) != 1 or len(turn.calls) != 1:
                            raise ValidationError("answer_call_count", "answer", "Return only one final answer call, without data tool calls.")
                        if pending_work and not closing:
                            raise ValidationError("answer_pending_work", "answer", "Complete pending metrics before finalizing.")
                        text, rendered_claims = render_answer(json.loads(final_calls[0].arguments), catalog, self.name)
                        if getattr(self, "numeric_requested", False) and catalog.facts and not any("fact_id" in c for c in rendered_claims):
                            raise ValidationError("numeric_selection_required", "fact_ids", "Select source facts for the requested numeric analysis, not proposed actions alone.")
                        turn.text, turn.calls = text, []
                        record("grounded_answer_rendered", agent=self.name, claims=len(rendered_claims))
                    except (ValueError, TypeError) as error:
                        last_action = "repairing source-bound answer selection"
                        preserve_rejection(error, "submit_grounded_answer", step + 1)
                        reject_calls(history, turn, json.dumps(repair_feedback(error)))
                        continue
                elif not turn.calls:
                    last_action = "repairing an unstructured final answer"
                    preserve_rejection(ValidationError("grounded_answer_required", "answer",
                        "Free-form output cannot be released; submit the structured answer tool instead.",
                        local_details={"expected": "submit_grounded_answer", **minimal_value(turn.text)}),
                        "free_form_answer", step + 1)
                    history.append({"role": "user", "content": "Use submit_grounded_answer; free-form factual text cannot be released."})
                    continue
            if closing and turn.calls:
                break
            if not turn.calls:
                if not turn.text.strip():
                    raise RuntimeError("The agent returned no answer.")
                if pending_work and not closing:
                    history.append({"role": "user", "content": "Some requested metrics remain unqueried. "
                        "Use the available tools to complete them; do not claim that unqueried data does not exist. " +
                        json.dumps({"numeric_coverage": self.numeric_coverage(evidence)})})
                    continue
                if not grounded:
                    self.last_result.diagnostics["last_unverified_text"] = turn.text
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
                result = AgentResult(self.name, question, turn.text, self.scope.__dict__, evidence, trace, self.mode)
                # Preserve only the minimized rejected-only history, not raw rejected prose.
                result.diagnostics.update({key: value for key, value in self.last_result.diagnostics.items()
                                           if key in {"rejected_attempts", "rejected_attempts_omitted"}})
                if grounded:
                    for entry in rejections[rejection_start:]:
                        entry.update(resolution="accepted_source_submission", accepted_model_turn=step + 1)
                    result.claims = rendered_claims
                    result.grounding = {"version": "source-facts-v1", "payload": json.loads(final_calls[0].arguments),
                                        "role": self.name, "semantic_quality": "requires_independent_review"}
                if hasattr(self, "numeric_coverage"):
                    result.diagnostics["numeric_coverage"] = self.numeric_coverage(evidence)
                return result
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
                if "citation_id" in result:
                    remember(result)
                for passage in result.get("passages", []):
                    remember(passage)
                for item in result.get("evidence", []):
                    remember(item)
                passages = getattr(self, "evidence_for_result", lambda result: [])(result)
                for passage in passages:
                    remember(passage)
                model_result = {**result, "passages": passages} if passages else result
                if len(json.dumps(model_result)) > 80_000:
                    raise RuntimeError("Tool result with cited passages exceeds the output context limit.")
                if passages:
                    trace[-1]["source_passages"] = passages
                history.append({"type": "function_call_output", "call_id": call.call_id,
                                "output": json.dumps(model_result, ensure_ascii=False)})
            if tool_errors:
                last_action += f" ({tool_errors} tool errors)"
        record("agent_turn_limit", agent=self.name, turns=step + 1)
        raise RuntimeError(f"{self.name} agent turn budget exceeded after {step + 1} model turns; "
                           f"last action: {last_action}. No unverified answer was returned.")
