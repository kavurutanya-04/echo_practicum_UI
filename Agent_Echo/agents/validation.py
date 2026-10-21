"""Bounded validation diagnostics without source text or provider payloads."""

import json


class ValidationError(ValueError):
    def __init__(self, code, field, message, **details):
        super().__init__(message)
        self.details = {"validation_code": code, "field": field, **details}


def validation_details(error):
    if isinstance(error, ValidationError):
        return error.details
    if isinstance(error, json.JSONDecodeError):
        return {"validation_code": "invalid_json", "field": "tool_arguments",
                "line": error.lineno, "column": error.colno}
    return {"validation_code": "invalid_structure", "field": "tool_arguments"}


def repair_feedback(error):
    # Only known application messages are echoed; arbitrary exceptions may hold data.
    return {"error": str(error) if isinstance(error, ValidationError) else "Return valid tool arguments.",
            **validation_details(error)}
