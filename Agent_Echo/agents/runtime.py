"""Bounded model/tool loop shared by the two independently configured specialists."""

from dataclasses import dataclass, field
import json
import re
import time


def function_tool(name, description, properties):
    return {"type": "function", "name": name, "description": description,
            "strict": True, "parameters": {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}}


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


class Specialist:
    def __init__(self, name, instructions, model, scope, definitions, handlers, mode="live", budget=None):
        self.name, self.instructions, self.model = name, instructions, model
        self.scope, self.definitions, self.handlers, self.mode = scope, definitions, handlers, mode
        self.budget = budget

    def run(self, question, initial_evidence=(), context=()):
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("Question must contain 1 to 4,000 characters.")
        history = [{"role": "user", "content": question}]
        history.extend(context)
        evidence, trace = list(initial_evidence), []
        known = {item["citation_id"] for item in evidence}
        budget = self.budget or RunBudget()
        instructions = self.instructions + "\nTrusted application scope: " + json.dumps(self.scope.__dict__)
        for step in range(7):
            budget.consume("model")
            turn = self.model.respond(instructions, history, self.definitions, require_tool=(step == 0 and not initial_evidence))
            history.extend(turn.output_items)
            if not turn.calls:
                if not turn.text.strip():
                    raise RuntimeError("The agent returned no answer.")
                cited = set(re.findall(r"\[([A-Za-z0-9_:-]+)\]", turn.text))
                unknown = cited - known
                if unknown or (evidence and not (cited & known)):
                    history.append({"role": "user", "content":
                        "Repair citation formatting. Use only evidence IDs returned by your tools in square brackets. "
                        "Ground findings in those sources; do not fabricate citations. Available IDs: " + ", ".join(sorted(known))})
                    continue
                return AgentResult(self.name, question, turn.text, self.scope.__dict__, evidence, trace, self.mode)
            if len(turn.calls) > 4 or len(trace) + len(turn.calls) > 12:
                raise RuntimeError("Agent tool-call budget exceeded.")
            for call in turn.calls:
                budget.consume("tool")
                try:
                    if call.name not in self.handlers:
                        raise ValueError("Tool is not available to this agent.")
                    arguments = json.loads(call.arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be an object.")
                    result = self.handlers[call.name](**arguments)
                    if len(json.dumps(result)) > 80_000:
                        raise ValueError("Result is too large. Select fewer columns or aggregate the query.")
                except (ValueError, TypeError) as error:
                    result = {"error": str(error)}
                trace.append({"tool": call.name, "arguments": call.arguments, "result": result})
                if "citation_id" in result:
                    evidence.append(result)
                    known.add(result["citation_id"])
                for passage in result.get("passages", []):
                    evidence.append(passage)
                    known.add(passage["citation_id"])
                for item in result.get("evidence", []):
                    evidence.append(item)
                    known.add(item["citation_id"])
                history.append({"type": "function_call_output", "call_id": call.call_id,
                                "output": json.dumps(result, ensure_ascii=False)})
        raise RuntimeError("Agent turn budget exceeded; no unverified answer was returned.")
