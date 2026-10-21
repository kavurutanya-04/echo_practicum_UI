"""Small Responses API adapter; configuration is read only when explicitly run."""

from dataclasses import dataclass, field
import json
from .execution_log import record
from .request_pacing import retry_after_seconds


class ConfigurationError(RuntimeError):
    pass


def request_failure(error):
    """Explain public error categories without echoing provider payloads or keys."""
    status = getattr(error, "status_code", None)
    body = getattr(error, "body", None)
    detail = body.get("error", body) if isinstance(body, dict) else {}
    if status == 403 and isinstance(detail, dict) and detail.get("type") == "FreeTierError" \
            and "within opencode" in str(detail.get("message", "")).lower():
        return RuntimeError("HTTP 403 (FreeTierError): OpenCode's free tier only works inside OpenCode; "
                            "it cannot be used for Echo's Python API requests. Select another provider.")
    if type(error).__name__ in {"APITimeoutError", "ReadTimeout", "ConnectTimeout", "TimeoutException", "TimeoutError"}:
        return RuntimeError("Model request timed out while waiting for the provider. "
                            "Key validity and model availability are not confirmed; no answer was accepted.")
    if type(error).__name__ == "APIConnectionError":
        return RuntimeError("Could not connect to the model API. Check network access, proxy/TLS settings and the configured endpoint.")
    reasons = {400: "The provider rejected the request parameters; check model and tool support.",
               401: "Authentication failed; check the selected provider's key.",
               403: "Access denied; check account permissions and API/free-tier restrictions.",
               404: "Model or endpoint not found; the catalog listing alone does not confirm a working endpoint.",
               429: "Rate limit or quota reached; check the selected provider's limits."}
    if isinstance(status, int):
        reason = "Provider service error; try again later." if status >= 500 else reasons.get(status, "The provider rejected the request.")
        return RuntimeError(f"Model request failed (HTTP {status}). {reason}")
    return RuntimeError("Chat/model request failed. Check the selected profile's key, endpoint, model access, limits and tool support.")


@dataclass
class ToolCall:
    call_id: str
    name: str
    arguments: str


@dataclass
class ModelTurn:
    text: str = ""
    calls: list = field(default_factory=list)
    output_items: list = field(default_factory=list)


class ResponsesModel:
    """Supports the GW Azure pattern and OpenAI through the same agent interface."""

    def __init__(self, client, model):
        self.client, self.model = client, model
        self.request_count, self.successful_requests = 0, 0

    @classmethod
    def from_environment(cls):
        # Compatibility name for older callers; JSON still selects the profile.
        from .connections import ModelRegistry
        registry = ModelRegistry()
        return registry.get("Cherry")

    def respond(self, instructions, history, tools, require_tool=False):
        self.request_count += 1
        try:
            response = self.client.responses.create(
                model=self.model, instructions=instructions, input=history, tools=tools,
                tool_choice=("required" if require_tool else "auto") if tools else "none",
                parallel_tool_calls=False, max_output_tokens=3500, store=False,
            )
        except Exception as error:
            # Provider errors can contain request data. Do not print their raw payload.
            raise request_failure(error) from None
        if response.status != "completed":
            raise RuntimeError("Model response did not complete; no answer was accepted.")
        self.successful_requests += 1
        calls = [ToolCall(item.call_id, item.name, item.arguments)
                 for item in response.output if item.type == "function_call"]
        return ModelTurn(response.output_text, calls,
                         [item.model_dump(exclude_none=True) for item in response.output])


class ChatModel:
    """Chat Completions adapter with provider tool-call metadata preserved."""

    def __init__(self, client, model, max_output_tokens=3500, reasoning_effort=None, clear_thinking=None,
                 request_pacer=None, rate_limit_retries=0):
        self.client, self.model = client, model
        self.request_pacer, self.rate_limit_retries = request_pacer, rate_limit_retries
        self.max_output_tokens = max_output_tokens
        self.request_options = {}
        if reasoning_effort is not None:
            if reasoning_effort not in {"low", "high", "max"}:
                raise ConfigurationError("Unsupported Chat Completions reasoning effort.")
            self.request_options["reasoning_effort"] = reasoning_effort
        if clear_thinking is not None:
            if not isinstance(clear_thinking, bool):
                raise ConfigurationError("clear_thinking must be a boolean.")
            self.request_options["extra_body"] = {"chat_template_kwargs": {"clear_thinking": clear_thinking}}
        self.request_count, self.successful_requests = 0, 0

    def respond(self, instructions, history, tools, require_tool=False):
        messages = [{"role": "system", "content": instructions}]
        for item in history:
            if item.get("type") == "chat_message":
                # Includes tool-call extra_content/thought signatures from the provider.
                messages.append(item["message"])
            elif item.get("type") == "function_call_output":
                messages.append({"role": "tool", "tool_call_id": item["call_id"], "content": item["output"]})
            elif "role" in item:
                messages.append(item)
            else:
                raise RuntimeError("Conversation items do not match the selected provider adapter.")
        definitions = [{"type": "function", "function": {key: tool[key]
            for key in ("name", "description", "parameters")}} for tool in tools]
        options = {"model": self.model, "messages": messages, "max_tokens": self.max_output_tokens}
        options.update(self.request_options)
        if definitions:
            options.update(tools=definitions, tool_choice="required" if require_tool else "auto")
        else:
            options["tool_choice"] = "none"
        for attempt in range(self.rate_limit_retries + 1):
            if self.request_pacer:
                self.request_pacer.acquire()
            self.request_count += 1
            try:
                response = self.client.chat.completions.create(**options)
                break
            except Exception as error:
                if getattr(error, "status_code", None) != 429 or not self.request_pacer:
                    raise request_failure(error) from None
                delay = retry_after_seconds(error, max(20, self.request_pacer.interval) * 2 ** attempt)
                # Preserve the cooldown even when this call has no retries left.
                self.request_pacer.defer(delay)
                if attempt == self.rate_limit_retries:
                    raise request_failure(error) from None
                record("request_rate_limit_retry", retry=attempt + 1, seconds=round(delay, 3), http_status=429)
        finish_reason = response.choices[0].finish_reason if response.choices else "no_choices"
        if finish_reason not in {"stop", "tool_calls"}:
            safe_reason = finish_reason if finish_reason in {
                "length", "content_filter", "function_call", "malformed_function_call", "no_choices"} else "unknown"
            record("model_response_rejected", adapter="chat", finish_reason=safe_reason)
        if finish_reason == "length":
            raise RuntimeError("Model output token budget exhausted before completion. Reasoning may consume "
                               "the output budget before visible text or tool calls; check max_output_tokens. "
                               "No answer was accepted.")
        if finish_reason not in {"stop", "tool_calls"}:
            raise RuntimeError(f"Model response did not complete (finish reason: {safe_reason}); no answer was accepted.")
        self.successful_requests += 1
        message = response.choices[0].message
        raw = message.model_dump(exclude_none=True)
        # DeepSeek thinking/tool turns require reasoning_content on subsequent calls.
        raw = {key: value for key, value in raw.items() if key in {"role", "content", "tool_calls", "reasoning_content"}}
        calls = [ToolCall(call.id, call.function.name, call.function.arguments)
                 for call in (message.tool_calls or [])]
        return ModelTurn(message.content or "", calls, [{"type": "chat_message", "message": raw}])


class ScriptedDemoModel:
    """Offline integration fixture, NOT a language model or natural-language evaluator."""

    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.step = 0

    def respond(self, instructions, history, tools, require_tool=False):
        if self.agent_name == "Original" and tools and tools[0]["name"] == "submit_plan":
            plan = {"needs_numbers": True, "needs_text": True, "include_chart": True,
                    "clarification_question": None, "clarification_basis": None, "metrics": []}
            call = ToolCall("demo-plan", "submit_plan", json.dumps(plan))
            return ModelTurn(calls=[call], output_items=[{"type": "function_call", "call_id": call.call_id,
                "name": call.name, "arguments": call.arguments}])
        self.step += 1
        if self.agent_name == "Lime":
            payload = json.loads(history[0]["content"])
            sources = [item for item in payload["evidence"] if item.get("sql") and item.get("rows")
                       and not item.get("truncated")]
            eligible = next((item for item in sources if all("Survey_Date" in row and "Mean_Score" in row
                and "Team" in row for row in item["rows"])), None)
            charts = [] if eligible is None else [{"source_id": eligible["citation_id"], "kind": "line",
                "x": "Survey_Date", "y": "Mean_Score", "series": "Team",
                "title": "Recognition survey trend (synthetic data)", "x_label": "Survey date",
                "y_label": "Mean recognition score", "unit": "Score (1-5)", "denominator": "Responses"}]
            plan = {"charts": charts, "reason": "Scripted chart choice; this checks evidence-bound rendering, not model judgment."
                if charts else "No eligible numeric table in the scripted fixture."}
            call = ToolCall("demo-visuals", "submit_visuals", json.dumps(plan))
            return ModelTurn(calls=[call], output_items=[{"type": "function_call", "call_id": call.call_id,
                "name": call.name, "arguments": call.arguments}])
        if self.agent_name == "ZeroSugar":
            payload = json.loads(history[0]["content"])
            report = {"decision": "accept", "ratings": {name: {"score": 3, "rationale": "Scripted fixture score; no LLM judgment was performed."}
                for name in ("Accuracy", "Relevance", "Completeness", "Clarity", "Instruction Following", "Usefulness", "Safety / Appropriateness")},
                "issues": [], "uncertainty": "Offline fixture: answer quality has not been assessed by a model."}
            report.update(finding_reviews=[{"finding_id": b["finding_id"], "decision": "supported",
                "citation_ids": b["citation_ids"], "reason": "Scripted fixture, not semantic validation."}
                for b in payload.get("findings", [])], repair_targets=[], clarification_question=None)
            call = ToolCall("demo-review", "submit_review", json.dumps(report))
            return ModelTurn(calls=[call], output_items=[{"type": "function_call", "call_id": call.call_id, "name": call.name, "arguments": call.arguments}])
        if self.agent_name == "Original":
            plan = [("ask_cherry", {"question": "Show quarterly recognition survey metrics."}),
                    ("ask_vanilla", {"question": "Find anonymous survey examples about recognition."})]
        elif self.agent_name == "Cherry":
            plan = [
                ("describe_schema", {}),
                ("execute_sql", {"sql": "SELECT Team, Survey_Date, Responses, Mean_Score, Favorable_Percent FROM survey_summary WHERE Dimension = 'Recognition' ORDER BY Survey_Date"}),
            ]
        elif self.agent_name == "Vanilla":
            plan = [("search_text", {"query": "recognition contributions acknowledge", "source": "HR_survey_comments", "dimension": "Recognition", "limit": 4})]
        else:
            raise ValueError("Unknown scripted demo role.")
        if self.step <= len(plan):
            name, arguments = plan[self.step - 1]
            call = ToolCall(f"demo-{self.step}", name, json.dumps(arguments))
            item = {"type": "function_call", "call_id": call.call_id,
                    "name": name, "arguments": call.arguments}
            return ModelTurn(calls=[call], output_items=[item])
        results = [json.loads(item["output"]) for item in history
                   if isinstance(item, dict) and item.get("type") == "function_call_output"]
        result = results[-1]
        if "error" in result:
            text = "Offline demo tool failed: " + result["error"]
        elif self.agent_name == "Original":
            citations = " ".join("[" + item["citation_id"] + "]" for response in results for item in response.get("evidence", [])[:1])
            text = "Offline scripted workflow: Cherry retrieved quarterly recognition metrics and Vanilla retrieved anonymous comments. " + citations + " The workflow preserves scope and evidence. No LLM analysis or quality evaluation was performed."
        elif self.agent_name == "Cherry":
            text = f"Offline scripted demo: retrieved {len(result['rows'])} quarterly recognition metric rows [{result['citation_id']}]. This checks tools and evidence flow, not LLM reasoning."
        else:
            passages = result["passages"]
            citations = " ".join("[" + p["citation_id"] + "]" for p in passages)
            text = f"Offline scripted demo: retrieved {len(passages)} anonymous recognition passages. {citations} These examples do not measure sentiment prevalence. No LLM interpretation was performed."
        return ModelTurn(text=text)
