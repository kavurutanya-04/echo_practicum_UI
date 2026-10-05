"""Small Responses API adapter; configuration is read only when explicitly run."""

from dataclasses import dataclass, field
import json
import os


class ConfigurationError(RuntimeError):
    pass


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

    @classmethod
    def from_environment(cls):
        # Compatibility entry point for older callers; all construction uses the registry.
        from .connections import ModelRegistry
        legacy = os.getenv("LLM_PROVIDER")
        aliases = {"azure": "gw_azure", "openai": "personal_openai", "google": "google_test"}
        if legacy and legacy.lower() not in aliases:
            raise ConfigurationError("LLM_PROVIDER must be azure, openai or google.")
        registry = ModelRegistry(force_profile=aliases.get(legacy.lower()) if legacy else None)
        return registry.get("Cherry")

    def respond(self, instructions, history, tools, require_tool=False):
        try:
            response = self.client.responses.create(
                model=self.model, instructions=instructions, input=history, tools=tools,
                tool_choice="required" if require_tool else "auto",
                parallel_tool_calls=False, max_output_tokens=3500, store=False,
            )
        except Exception:
            # Provider errors can contain request data. Do not print their raw payload.
            raise RuntimeError("Model request failed. Check the configured deployment, access and API support.") from None
        if response.status != "completed":
            raise RuntimeError("Model response did not complete; no answer was accepted.")
        calls = [ToolCall(item.call_id, item.name, item.arguments)
                 for item in response.output if item.type == "function_call"]
        return ModelTurn(response.output_text, calls,
                         [item.model_dump(exclude_none=True) for item in response.output])


class ChatModel:
    """Google's documented OpenAI-compatible API, with provider metadata preserved."""

    def __init__(self, client, model):
        self.client, self.model = client, model

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
        options = {"model": self.model, "messages": messages, "max_tokens": 3500}
        if definitions:
            options.update(tools=definitions, tool_choice="required" if require_tool else "auto")
        try:
            response = self.client.chat.completions.create(**options)
        except Exception:
            raise RuntimeError("Google model request failed. Check model access and tool support.") from None
        if not response.choices or response.choices[0].finish_reason not in {"stop", "tool_calls"}:
            raise RuntimeError("Model response did not complete; no answer was accepted.")
        message = response.choices[0].message
        raw = message.model_dump(exclude_none=True)
        raw = {key: value for key, value in raw.items() if key in {"role", "content", "tool_calls"}}
        calls = [ToolCall(call.id, call.function.name, call.function.arguments)
                 for call in (message.tool_calls or [])]
        return ModelTurn(message.content or "", calls, [{"type": "chat_message", "message": raw}])


class ScriptedDemoModel:
    """Offline integration fixture, NOT a language model or natural-language evaluator."""

    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.step = 0

    def respond(self, instructions, history, tools, require_tool=False):
        self.step += 1
        if self.agent_name == "ZeroSugar":
            report = {"decision": "accept", "ratings": {name: {"score": 3, "rationale": "Scripted fixture score; no LLM judgment was performed."}
                for name in ("Accuracy", "Relevance", "Completeness", "Clarity", "Instruction Following", "Usefulness", "Safety / Appropriateness")},
                "issues": [], "uncertainty": "Offline fixture: answer quality has not been assessed by a model."}
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
