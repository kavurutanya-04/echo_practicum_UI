"""Bounded diagnostics; answer/planning context uses explicit redaction, never raw payloads."""

import json
import re


class ValidationError(ValueError):
    def __init__(self, code, field, message, *, local_details=None, **details):
        super().__init__(message)
        self.details = {"validation_code": code, "field": field, **details}
        # Never merge local diagnostic fragments into log/repair metadata.
        self.local_details = local_details or {}


def validation_details(error):
    if isinstance(error, ValidationError):
        return error.details
    if isinstance(error, json.JSONDecodeError):
        return {"validation_code": "invalid_json", "field": "tool_arguments",
                "line": error.lineno, "column": error.colno}
    return {"validation_code": "invalid_structure", "field": "tool_arguments"}


def safe_validation_details(error):
    """Explicit persistence allowlist; repair feedback can retain its existing contract."""
    details, result = validation_details(error), {}
    for key in ("validation_code", "field", "source_id", "finding_id"):
        value = details.get(key)
        pattern = (r"(?:SQL\d+|SENTIMENT\d+|F\d+|[A-Za-z_][A-Za-z0-9_]*:[A-Za-z0-9_-]+)"
                   if key in {"source_id", "finding_id"} else r"[A-Za-z0-9_.\[\] /:-]+")
        if isinstance(value, str) and len(value) <= 160 and re.fullmatch(pattern, value):
            result[key] = value
    for key in ("item_index", "source_index", "expected_count", "actual_count", "max_characters", "actual_characters", "line", "column", "unexpected_field_count"):
        if type(details.get(key)) is int and details[key] >= 0:
            result[key] = details[key]
    if isinstance(details.get("missing_fields"), list):
        result["missing_fields"] = [name for name in details["missing_fields"] if isinstance(name, str) and name in
                                    {"fact_ids", "interpretations", "proposals"}]
    return result


def repair_feedback(error):
    # Only known application messages are echoed; arbitrary exceptions may hold data.
    feedback = {"error": str(error) if isinstance(error, ValidationError) else "Return valid tool arguments.",
                **validation_details(error)}
    if isinstance(error, ValidationError):
        # Only minimized/allowlisted fragments may reach model repair, never raw prose.
        detail = rejection_diagnostic(error, "repair", "repair", 0, 0)["detail"]
        if detail:
            feedback["condition"] = detail
        feedback["correction"] = "Correct the indicated field in your previous submission; preserve already valid fields."
    return feedback


def planning_value(value):
    """Retain bounded diagnostic values, redacting recognizable private identifiers."""
    if isinstance(value, str):
        patterns = (
            r"(?i)\b(?:bearer\s+|(?:api[_ -]?key|password|secret|token)\s*[:=]\s*)[^\s,;]+",
            r"\b(?:sk-|AIza)[A-Za-z0-9_-]+",
            r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"(?i)\b(?:employee[_ -]?id\s*[:=]?\s*[A-Za-z0-9_-]+|E\d{3,})\b",
            r"(?<!\w)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b",
        )
        redacted = value
        for pattern in patterns:
            redacted = re.sub(pattern, "[REDACTED]", redacted)
        return {"value_type": "str", "value": redacted[:1200],
                "redacted": redacted != value, "truncated": len(redacted) > 1200}
    if isinstance(value, dict):
        fields = {"missing_field", "missing_detail", "blocking_reason", "request_excerpt"}
        return {"value_type": "dict", "value": {key: planning_value(item)
                for key, item in value.items() if key in fields},
                "omitted_field_count": len(set(value) - fields)}
    if value is None or type(value) in (bool, int, float):
        return {"value_type": type(value).__name__, "value": value}
    return {"value_type": type(value).__name__, "content_omitted": True,
            **({"value_length": len(value)} if isinstance(value, list) else {})}


def answer_context(payload, field):
    """Retain the indicated narrative item, not the full model request or answer payload."""
    if not isinstance(payload, dict):
        return minimal_value(payload)
    match = re.match(r"^(interpretations|proposals)\[(\d+)\]", field or "")
    if match:
        items, index = payload.get(match[1]), int(match[2])
        if isinstance(items, list) and index < len(items):
            item = items[index]
            if not isinstance(item, dict):
                return minimal_value(item)
            context = {key: planning_value(item[key]) for key in ("text", "quote") if key in item}
            refs = item.get("citation_ids")
            context["citation_ids"] = ([planning_value(ref) for ref in refs[:32]]
                                       if isinstance(refs, list) else planning_value(refs))
            if isinstance(refs, list):
                context["citation_ids_omitted"] = max(0, len(refs) - 32)
            return context
    if field == "fact_ids" and isinstance(payload.get("fact_ids"), list):
        return {"fact_ids": [planning_value(key) for key in payload["fact_ids"][:24]],
                "omitted": max(0, len(payload["fact_ids"]) - 24)}
    return {"present_fields": [key for key in ("fact_ids", "interpretations", "proposals") if key in payload],
            "unexpected_field_count": len(set(payload) - {"fact_ids", "interpretations", "proposals"})}


def diagnostic_feedback(feedback):
    """Application feedback has declared keys; redact any free string values before persistence."""
    return {key: planning_value(value) if isinstance(value, str) else value
            for key, value in feedback.items()}


def minimal_value(value):
    """Describe a rejected value without retaining arbitrary employee/provider text."""
    result = {"value_type": type(value).__name__, "content_omitted": True}
    if isinstance(value, (str, list, dict)):
        result["value_length"] = len(value)
    # Only the renderer's fixed-format technical identifiers are retained verbatim.
    if isinstance(value, str) and re.fullmatch(r"FACT_[0-9a-f]{12}", value):
        result.update(safe_fragment=value, content_omitted=False)
    return result


def numeric_fragment(text, match):
    """Retain only an allowlisted quarter/keyword, not names, numbers or surrounding prose."""
    result = {"match_start": match.start(), "match_end": match.end(), "content_omitted": True,
              "match_kind": "digit" if match.group().isdigit() else "quantifier_keyword"}
    for quarter in re.finditer(r"\bQ[1-4]\b", text, re.I):
        if quarter.start() <= match.start() < quarter.end():
            result["safe_fragment"] = quarter.group().upper()
            break
    if match.group().casefold() in {"percent", "percentage", "percentage points", "majority", "minority",
                                  "all employees", "everyone", "every quarter", "always", "never"}:
        result["safe_fragment"] = match.group().casefold()
    return result


def rejection_diagnostic(error, agent, tool, model_turn, rejection_index):
    """Local, rejected-only record. Full arguments/prompts/quotes are deliberately absent."""
    result = {"agent": agent, "tool": tool, "model_turn": model_turn, "rejection_index": rejection_index,
              "status": "rejected_unverified", "resolution": "unresolved", **safe_validation_details(error)}
    # These messages are fixed application strings; never use arbitrary exception text.
    result["reason"] = str(error) if isinstance(error, ValidationError) else "Return valid tool arguments."
    if isinstance(error, ValidationError):
        # Local details are constructed by validators from minimal_value/numeric_fragment,
        # counts and fixed expectations, never copied from raw model tool arguments.
        detail = error.local_details
        result["detail"] = {key: detail[key] for key in ("value_length", "match_start", "match_end")
                            if type(detail.get(key)) is int and detail[key] >= 0}
        for key, options in {"value_type": {"str", "list", "dict", "int", "float", "bool", "NoneType"},
                             "match_kind": {"digit", "quantifier_keyword"}}.items():
            if isinstance(detail.get(key), str) and detail[key] in options:
                result["detail"][key] = detail[key]
        if type(detail.get("content_omitted")) is bool:
            result["detail"]["content_omitted"] = detail["content_omitted"]
        fragment = detail.get("safe_fragment")
        if isinstance(fragment, str) and re.fullmatch(
                r"FACT_[0-9a-f]{12}|Q[1-4]|percent|percentage|percentage points|majority|minority|all employees|everyone|every quarter|always|never", fragment):
            result["detail"]["safe_fragment"] = fragment
    return result
