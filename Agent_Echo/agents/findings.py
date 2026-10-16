"""Stable review units: partial release never reconstructs a rejected draft."""

import re


def clarification_question(value):
    """Nullable-tool interoperability: never ask a manager the literal 'None'."""
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError("Clarification must be a bounded question or null.")
    value = value.strip()
    if value.casefold() in {"", "none", "null", "n/a", "not applicable"}:
        return None
    return value


def normalize_citations(text, known):
    """Normalize explicit references to known sources, never invent new sources."""
    for source in sorted(known, key=len, reverse=True):
        escaped = re.escape(source)
        text = re.sub(r"`+\s*"+escaped+r"\s*`+", lambda _: "["+source+"]", text)
        text = re.sub(r"【\s*"+escaped+r"\s*】", lambda _: "["+source+"]", text)
    def expand(match):
        ids = [part.strip() for part in match[1].split(",")]
        return " ".join("["+key+"]" for key in ids) if all(key in known for key in ids) else match[0]
    return re.sub(r"\[([^\[\]\n]+,[^\[\]\n]+)\]", expand, text)


def cited_findings(answer):
    """Review substantive blocks, including uncited ones; skip plain headings only."""
    findings = []
    for text in re.split(r"\n\s*\n", answer.strip()):
        if not text.strip():
            continue
        if "\n" not in text and not re.search(r"\d", text) and len(text) < 90 \
                and (re.fullmatch(r"\*\*[^*]+\*\*:?", text) or re.fullmatch(r"#{1,6}\s+[^\n]+", text)):
            continue
        citations = sorted(set(re.findall(r"\[([A-Za-z0-9_:-]+)\]", text)))
        findings.append({"finding_id": f"F{len(findings)+1}", "text": text,
                         "citation_ids": citations})
    if len(findings) > 32:
        raise ValueError("Answer has too many finding blocks; narrow or summarize the answer.")
    return findings


def safe_follow_up(targets):
    messages = {"Cherry": "The numerical calculation or its population still requires correction.",
                "Vanilla": "The textual interpretation or its source coverage still requires review.",
                "Lime": "The chart needs correction before it can be released.",
                "Original": "Some conclusions or their presentation still require correction.",
                "clarify": "A necessary part of the request needs clarification."}
    return [messages[t] for t in sorted(set(targets)) if t in messages]
