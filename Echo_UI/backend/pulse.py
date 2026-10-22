"""Team pulse: an Amazon-style "what people are saying" summary of survey comments.

Managers never see individual comments. They see, per survey topic:
  * a deterministic mood split from the comments' own 1-5 response scores, and
  * a few AI-written theme bullets with rough proportions ("most", "some", "a few"),
    generated once per scope and cached. Bullets that copy wording from any comment are dropped.
Groups below Echo's minimum size are suppressed by Echo's own ScopedData layer.
"""

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MIN_COMMENTS = 5
MAX_COMMENTS_PER_TOPIC = 120
SHARES = ("most", "many", "some", "a few")
SUMMARY_MODEL = os.getenv("ECHO_UI_SUMMARY_MODEL", "gemini-3.1-flash-lite")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """You summarize anonymous employee survey comments for a team manager, like a product-review summary.
Rules:
- Describe patterns only. Never quote, never copy phrases of five or more words from any comment.
- Never mention or hint at individuals, names, roles, schedules or any detail that could identify someone.
- Only report a theme if at least two comments express it.
- For each theme give "share": one of "most", "many", "some", "a few", reflecting how many comments express it.
- Write plainly, at most 18 words per theme, 2 to 4 themes per topic, balanced between positives and concerns that appear.
- "headline" is one short sentence (max 14 words) on the overall mood for that topic.
Return JSON only, matching the schema."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {"topics": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "topic": {"type": "STRING"},
        "headline": {"type": "STRING"},
        "themes": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "text": {"type": "STRING"}, "share": {"type": "STRING", "enum": list(SHARES)},
            "tone": {"type": "STRING", "enum": ["positive", "concern", "mixed"]}},
            "required": ["text", "share", "tone"]}}},
        "required": ["topic", "headline", "themes"]}}},
    "required": ["topics"],
}


def _words(text):
    return re.findall(r"[a-z']+", text.lower())


def _copies_comment(text, shingles):
    words = _words(text)
    return any(" ".join(words[i:i + 5]) in shingles for i in range(len(words) - 4))


def comment_groups(data):
    """Scoped comments grouped by survey topic, using Echo's own access rules."""
    columns, rows = data.survey_rows(comments=True)
    groups = {}
    for row in rows:
        item = dict(zip(columns, row))
        groups.setdefault(item["Dimension"], []).append(item)
    return groups


def mood(groups):
    """Deterministic split from each comment's own 1-5 score; no model involved."""
    topics = []
    for topic, items in sorted(groups.items()):
        scores = [item["Response_Score"] for item in items if isinstance(item["Response_Score"], (int, float))]
        if topic == "eNPS" or len(scores) < MIN_COMMENTS:
            continue
        total = len(scores)
        topics.append({
            "topic": topic, "responses": total,
            "positive": round(100 * sum(s >= 4 for s in scores) / total),
            "neutral": round(100 * sum(s == 3 for s in scores) / total),
            "negative": round(100 * sum(s <= 2 for s in scores) / total),
        })
    return topics


def cache_path(cache_dir, scope):
    key = f"{scope.manager_id}_{scope.start_date}_{scope.end_date}"
    return Path(cache_dir) / f"pulse_{key}.json"


def generate_themes(groups, api_key):
    """One model call for all topics; returns (topics, model) or raises RuntimeError."""
    payload, shingles = {}, set()
    for topic, items in groups.items():
        if topic == "eNPS" or len(items) < MIN_COMMENTS:
            continue
        # Most recent first, so a capped topic reflects current views.
        items = sorted(items, key=lambda i: i["Survey_Date"], reverse=True)[:MAX_COMMENTS_PER_TOPIC]
        texts = [i["Response_Text"].split("\n", 1)[-1].strip() for i in items if i["Response_Text"]]
        payload[topic] = texts
        for text in texts:
            words = _words(text)
            shingles.update(" ".join(words[i:i + 5]) for i in range(len(words) - 4))
    if not payload:
        return [], SUMMARY_MODEL
    body = {
        "systemInstruction": {"parts": [{"text": PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps({"topics": payload}, ensure_ascii=False)}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0.2},
    }
    request = urllib.request.Request(ENDPOINT.format(model=SUMMARY_MODEL), data=json.dumps(body).encode(),
                                     headers={"x-goog-api-key": api_key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
        text = "".join(part.get("text", "") for part in result["candidates"][0]["content"]["parts"])
        topics = json.loads(text)["topics"]
    except urllib.error.HTTPError as error:
        raise RuntimeError({429: "The summary model's daily limit is used up; try again tomorrow.",
                            503: "The summary model is busy; try again in a few minutes."}.get(
                                error.code, f"The summary model returned HTTP {error.code}.")) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Could not reach the summary model. Check the network (campus networks may block it).") from None
    except (KeyError, IndexError, ValueError):
        raise RuntimeError("The summary model returned an unexpected response.") from None
    cleaned = []
    for topic in topics:
        if topic.get("topic") not in payload:
            continue
        themes = [t for t in topic.get("themes", [])
                  if t.get("share") in SHARES and t.get("text") and not _copies_comment(t["text"], shingles)][:4]
        headline = topic.get("headline", "")
        if _copies_comment(headline, shingles):
            headline = ""
        cleaned.append({"topic": topic["topic"], "headline": headline, "themes": themes,
                        "comments_used": len(payload[topic["topic"]])})
    return cleaned, SUMMARY_MODEL


def pulse(data, scope, cache_dir, api_key=None, generate=False):
    groups = comment_groups(data)
    result = {"scope": scope.__dict__, "mood": mood(groups), "themes": None, "generated_at": None,
              "model": None, "error": None}
    path = cache_path(cache_dir, scope)
    fingerprint = hashlib.sha256(json.dumps(sorted((k, len(v)) for k, v in groups.items())).encode()).hexdigest()[:16]
    cached = None
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if cached and cached.get("fingerprint") == fingerprint:
        result.update(themes=cached["themes"], generated_at=cached["generated_at"], model=cached["model"])
    if not generate:
        return result
    # generate=True rewrites the summary; on failure the cached one (if any) is kept and returned.
    if not api_key:
        result["error"] = "No Google API key is configured for AI summaries."
        return result
    try:
        themes, model = generate_themes(groups, api_key)
    except RuntimeError as error:
        result["error"] = str(error)
        return result
    stamp = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fingerprint": fingerprint, "themes": themes, "generated_at": stamp, "model": model},
                               indent=2), encoding="utf-8")
    result.update(themes=themes, generated_at=stamp, model=model)
    return result
