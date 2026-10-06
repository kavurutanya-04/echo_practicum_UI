"""A real minimal function-call probe, never an offline substitute."""

import json
from .connections import AGENTS
from .runtime import function_tool


def check_connections(registry, roles=AGENTS):
    results, checked = {}, {}
    tools = [function_tool("connection_check", "Confirm that function calling works.", {
        "status": {"type": "string", "enum": ["ok"]}})]
    for role in roles:
        model = registry.get(role)
        profile = registry.profile_for(role)
        if profile not in checked:
            turn = model.respond("Call connection_check exactly once with status='ok'. This is a connection probe; no employee data is supplied.",
                [{"role": "user", "content": "Check API access and tool calling."}], tools, True)
            if len(turn.calls) != 1 or turn.calls[0].name != "connection_check" or json.loads(turn.calls[0].arguments) != {"status": "ok"}:
                raise RuntimeError("The live connection probe did not return the required function call.")
            checked[profile] = {"status": "live_tool_call_confirmed", "profile": profile, "model": model.model}
        results[role] = checked[profile]
    return {"roles": results, "execution": registry.execution_summary(),
            "note": "Actual API calls; no analytic accuracy or embedding compatibility was tested."}
