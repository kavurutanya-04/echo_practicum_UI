"""Source-bound facts, controlled numeric rendering and claim-level provenance.

This validates reproducibility, not the semantic correctness of arbitrary SQL or
model interpretations. Those still need independent review and human evaluation.
"""

from decimal import Decimal
from datetime import date
import hashlib
import itertools
import json
import math
import re

from .validation import ValidationError, minimal_value, numeric_fragment


def fail(code, field, message, **details):
    raise ValidationError(code, field, message, **details)


def stable_id(kind, value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return kind + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def fmt(value):
    value = Decimal(str(value))
    return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else str(value)


def cell(value):
    # Preserve literal source strings without breaking table or citation syntax.
    if value is None:
        return "Unavailable"
    return str(value).replace("|", "\\|").replace("\n", " ").replace("[", "&#91;").replace("]", "&#93;")


def citations(ids):
    return " ".join("[" + key + "]" for key in sorted(set(ids)))


class FactCatalog:
    def __init__(self, evidence, scope):
        self.scope = scope
        self.sources = {}
        self.facts = {}
        surveys = []
        for source in evidence:
            key = source.get("citation_id")
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_:-]+", key):
                fail("source_identity", "evidence", "Evidence needs a valid source identifier.")
            if key in self.sources and self.sources[key] != source:
                fail("source_collision", "evidence", "One source identifier has conflicting records.")
            self.sources[key] = source
            if "scope" in source and source["scope"] != scope:
                fail("source_scope", "evidence", "Evidence scope differs from the authorized scope.")
            if source.get("truncated"):
                continue
            rows = source.get("rows")
            if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
                continue
            if source.get("producer") != "Cherry" and source.get("kind") != "survey_sentiment":
                continue
            refs = [key]
            semantics = "catalog metric" if source.get("metric_id") else \
                "provisional sentiment aggregation" if source.get("kind") == "survey_sentiment" else \
                "exploratory SQL; metric grain and meaning require independent review"
            columns = list(rows[0])
            if any(list(row) != columns for row in rows):
                fail("table_columns", "evidence.rows", "Table rows need consistent columns.")
            table = "Source rows (" + semantics + ") " + citations(refs) + "\n\n"
            table += "| " + " | ".join(cell(c) for c in columns) + " |\n"
            table += "| " + " | ".join("---" for _ in columns) + " |\n"
            table += "\n".join("| " + " | ".join(cell(row[c]) for c in columns) + " |" for row in rows)
            self.add("table", table, refs, {"rows": rows, "columns": columns}, semantics)
            dimension = source.get("metric_arguments", {}).get("dimension")
            for index, row in enumerate(rows):
                context = ", ".join(cell(row[k]) for k in ("Team", "Dimension", "Survey_Date", "Week_Start") if row.get(k) is not None)
                if dimension:
                    context = cell(dimension) + (", " + context if context else "")
                for column, value in row.items():
                    if number(value):
                        text = (context + ": " if context else "Source row " + str(index + 1) + ": ")
                        if semantics.startswith("exploratory"):
                            text = "Exploratory SQL output (metric meaning unvalidated): " + text
                        text += cell(column) + " = " + fmt(value) + ". " + citations(refs)
                        unit = "unspecified in exploratory query"
                        if source.get("metric_id") == "survey_trend":
                            unit = {"Responses": "survey responses", "Mean_Score": "recorded score points",
                                    "Favorable_Percent": "percent of responses rated 4 or 5"}.get(column, "source-defined")
                        elif source.get("metric_id") == "cross_team_contributions":
                            unit = "distinct cross-team contributions"
                        elif source.get("kind") == "survey_sentiment":
                            unit = "percent of eligible comments" if column.endswith("_percent") else "eligible comments"
                        self.add("observed", text, refs, {"row": index, "column": column, "value": value, "unit": unit}, semantics)
            if source.get("metric_id") == "survey_trend" and dimension:
                for row in rows:
                    if row.get("Team") is not None and row.get("Survey_Date") is not None:
                        surveys.append((dimension, row, key))
        self.survey_comparisons(surveys)
        if len(self.facts) > 1024:
            fail("fact_catalog_size", "evidence", "Too many facts; narrow or aggregate the requested evidence.")

    def add(self, kind, text, refs, operation, semantics="catalog metric"):
        fact = {"kind": kind, "text": text, "citation_ids": sorted(set(refs)),
                "operation": operation, "scope": self.scope, "query_semantics": semantics,
                "source_metrics": [{"citation_id": k, "metric_id": self.sources[k].get("metric_id"),
                    "arguments": self.sources[k].get("metric_arguments", {})} for k in sorted(set(refs))]}
        identity = stable_id("FACT_", fact)
        self.facts[identity] = {"fact_id": identity, **fact}

    def survey_comparisons(self, rows):
        groups = {}
        for dimension, row, key in rows:
            group = groups.setdefault((dimension, row["Team"]), {})
            date = row["Survey_Date"]
            if date in group and group[date][0] != row:
                fail("survey_duplicate_date", "evidence.rows", "Conflicting rows for a survey dimension, team and date.")
            group[date] = (row, key)
        for (dimension, team), dates in groups.items():
            ordered = sorted(dates)
            pairs = list(zip(ordered, ordered[1:]))
            if len(ordered) > 2:
                pairs.append((ordered[0], ordered[-1]))
            for start, end in pairs:
                before, a = dates[start]
                after, b = dates[end]
                for column, unit in (("Mean_Score", "score points"), ("Favorable_Percent", "percentage points")):
                    if not number(before.get(column)) or not number(after.get(column)):
                        continue
                    delta = Decimal(str(after[column])) - Decimal(str(before[column]))
                    direction = "increased" if delta > 0 else "decreased" if delta < 0 else "was unchanged"
                    text = f"{cell(dimension)} ({cell(team)}), {start} to {end}: {column} {direction}"
                    if delta:
                        text += f" by {fmt(abs(delta))} {unit}"
                    text += f", from {fmt(before[column])} to {fmt(after[column])}. " + citations([a, b])
                    self.add("calculated", text, [a, b], {"type": "difference", "column": column,
                        "start": start, "end": end, "before": before[column], "after": after[column],
                        "delta": str(delta), "unit": unit})
        for (first, team), (second, other_team) in itertools.combinations(sorted(groups), 2):
            if team != other_team:
                continue
            a_dates, b_dates = groups[first, team], groups[second, team]
            matched = sorted(a_dates.keys() & b_dates.keys())
            all_dates = sorted(a_dates.keys() | b_dates.keys())
            refs = [item[1] for item in [*a_dates.values(), *b_dates.values()]]
            combined_rows = []
            header = ["Survey date"] + [f"{dimension}: {column}" for dimension in (first, second)
                                         for column in ("Responses", "Mean_Score", "Favorable_Percent")]
            for date in all_dates:
                values = [date]
                for dates in (a_dates, b_dates):
                    row = dates[date][0] if date in dates else {}
                    values.extend(row.get(c) for c in ("Responses", "Mean_Score", "Favorable_Percent"))
                combined_rows.append(values)
            table = f"Survey comparison table ({cell(team)}); mean scores use the recorded scale and favorable values are percentages. " + citations(refs)
            table += "\n\n| " + " | ".join(cell(c) for c in header) + " |\n"
            table += "| " + " | ".join("---" for _ in header) + " |\n"
            table += "\n".join("| " + " | ".join(cell(v) for v in row) + " |" for row in combined_rows)
            self.add("table", table, refs, {"type": "survey_comparison_table", "columns": header, "rows": combined_rows})
            for column, unit in (("Mean_Score", "score points"), ("Favorable_Percent", "percentage points")):
                counts, refs = {"higher": 0, "lower": 0, "equal": 0}, []
                for date in matched:
                    a, a_id = a_dates[date]
                    b, b_id = b_dates[date]
                    if not number(a.get(column)) or not number(b.get(column)):
                        continue
                    delta = Decimal(str(a[column])) - Decimal(str(b[column]))
                    direction = "higher" if delta > 0 else "lower" if delta < 0 else "equal"
                    counts[direction] += 1
                    refs.extend([a_id, b_id])
                    relation = direction + (" to" if direction == "equal" else " than")
                    text = f"On {date} ({cell(team)}), {cell(first)} {column} ({fmt(a[column])}) was {relation} "
                    text += f"{cell(second)} ({fmt(b[column])}); difference = {fmt(delta)} {unit}. " + citations([a_id, b_id])
                    self.add("calculated", text, [a_id, b_id], {"type": "comparison", "date": date,
                        "column": column, "first": first, "second": second, "delta": str(delta), "unit": unit})
                if refs:
                    text = f"Across {sum(counts.values())} matched survey dates ({cell(team)}), {cell(first)} {column} "
                    text += f"was higher than {cell(second)} on {counts['higher']} dates, lower on {counts['lower']}, "
                    text += f"and equal on {counts['equal']}. " + citations(refs)
                    self.add("calculated", text, refs, {"type": "comparison_coverage", "column": column,
                        "first": first, "second": second, "counts": counts})

    def public(self):
        return [{k: fact[k] for k in ("fact_id", "kind", "text", "query_semantics")} for fact in self.facts.values()]


def answer_schema(role):
    narrative = {"type": "array", "maxItems": 12, "items": {"type": "object", "properties": {
        "text": {"type": "string", "minLength": 1, "maxLength": 600},
        "citation_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "quote": {"type": ["string", "null"], "maxLength": 400}},
        "required": ["text", "citation_ids", "quote"], "additionalProperties": False}}
    return {"fact_ids": {"type": "array", "maxItems": 24, "items": {"type": "string"}},
            "interpretations": narrative, "proposals": narrative}


def narrative_number(text, proposal=False):
    """Skip quarter/ISO-date references, not analytic quantities; meaning is reviewed."""
    temporal = []
    for match in re.finditer(r"\b(?:\d{4}-\d{2}-\d{2}|\d{4}-Q[1-4]|Q[1-4](?:\s+\d{4})?)\b", text, re.I):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", match.group()):
            try:
                date.fromisoformat(match.group())
            except ValueError:
                continue
        temporal.append(match.span())
    pattern = r"\d|\b(?:percent|percentage points)\b" if proposal else \
        r"\d|\b(?:percent|percentage|majority|minority|all employees|everyone|every quarter|always|never)\b"
    return next((match for match in re.finditer(pattern, text, re.I)
                 if not any(start <= match.start() < end for start, end in temporal)), None)


def render_answer(payload, catalog, role):
    if role not in {"Original", "Cherry", "Vanilla"}:
        fail("answer_role", "role", "Only Original, Cherry and Vanilla use this answer contract.")
    if not isinstance(payload, dict) or set(payload) != {"fact_ids", "interpretations", "proposals"}:
        required = {"fact_ids", "interpretations", "proposals"}
        fail("answer_fields", "answer", "Return fact_ids, interpretations and proposals only.",
             missing_fields=sorted(required - set(payload)) if isinstance(payload, dict) else sorted(required),
             unexpected_field_count=len(set(payload) - required) if isinstance(payload, dict) else 0)
    chosen = payload["fact_ids"]
    if not isinstance(chosen, list):
        fail("fact_ids_type", "fact_ids", "fact_ids must be a list of existing catalog identifiers.",
             local_details={"expected_type": "list", **minimal_value(chosen)})
    if len(chosen) > 24:
        fail("fact_ids_count", "fact_ids", "Select at most 24 fact IDs.", expected_count=24, actual_count=len(chosen))
    for index, key in enumerate(chosen):
        if not isinstance(key, str):
            fail("fact_id_type", "fact_ids", "Each fact ID must be a string.", item_index=index,
                 local_details={"expected_type": "str", **minimal_value(key)})
        if key not in catalog.facts:
            fail("fact_id_unknown", "fact_ids", "The selected identifier is absent from the supplied fact catalog.",
                 item_index=index, local_details={"expected": "existing catalog fact ID", **minimal_value(key)})
    claims = []
    for key in dict.fromkeys(chosen):
        fact = catalog.facts[key]
        sources = [catalog.sources[k] for k in fact["citation_ids"]]
        if role == "Cherry" and any(s.get("producer") != "Cherry" for s in sources):
            fail("fact_role", "fact_ids", "Cherry may select only its numeric source facts.")
        if role == "Vanilla" and any(s.get("producer") == "Cherry" for s in sources):
            fail("fact_role", "fact_ids", "Vanilla may select text or sentiment sources, not Cherry's SQL facts.")
        claims.append({**fact, "validation": "source_reproducible"})
    for kind in ("interpretations", "proposals"):
        items = payload[kind]
        if not isinstance(items, list):
            fail("narrative_type", kind, "Narrative fields must be lists.",
                 local_details={"expected_type": "list", **minimal_value(items)})
        if len(items) > 12:
            fail("narrative_count", kind, "A narrative list may contain at most 12 items.",
                 expected_count=12, actual_count=len(items))
        if role == "Cherry" and items:
            fail("narrative_role", kind, "Cherry selects numeric facts only; this narrative list must be empty.",
                 expected_count=0, actual_count=len(items))
        for index, item in enumerate(items):
            path = kind + f"[{index}]"
            if not isinstance(item, dict) or set(item) != {"text", "citation_ids", "quote"}:
                fail("narrative_fields", path, "Each narrative claim requires text, citation_ids and quote.", item_index=index)
            text, refs, quote = item["text"], item["citation_ids"], item["quote"]
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= 600 or "\n" in text:
                fail("narrative_text", path + ".text", "Use one short sentence per narrative claim (1-600 characters, no newline).",
                     item_index=index, local_details={"expected": "1-600 characters, no newline", **minimal_value(text)})
            if not isinstance(refs, list):
                fail("narrative_sources_type", path + ".citation_ids", "Use a list of source IDs, without citation brackets.", item_index=index)
            if not refs:
                fail("narrative_sources_empty", path + ".citation_ids", "Select an existing source ID for this narrative item.", item_index=index)
            for source_index, identity in enumerate(refs):
                if not isinstance(identity, str):
                    fail("narrative_source_type", path + f".citation_ids[{source_index}]", "Each source ID must be a string.", item_index=index, source_index=source_index)
                if identity not in catalog.sources:
                    fail("narrative_source_unknown", path + f".citation_ids[{source_index}]", "Replace this ID with an available source ID, exactly as supplied and without brackets. Fact IDs belong in fact_ids.", item_index=index, source_index=source_index)
            # No source IDs embedded in model prose: code owns citation placement.
            if re.search(r"\[[^\]]+\]", text):
                fail("embedded_citation", path + ".text", "Put source identifiers in citation_ids, not in the text.", item_index=index)
            if kind == "interpretations":
                if len(refs) != 1:
                    fail("interpretation_scope", path + ".citation_ids", "Use one source excerpt per individual interpretation; do not infer a population theme.", item_index=index)
                match = narrative_number(text)
                if match:
                    fail("numeric_interpretation", path + ".text", "A digit or quantifier keyword triggered the interpretation rule; this alone does not prove a false claim. Select numerical comparisons as catalog facts.",
                         item_index=index, local_details=numeric_fragment(text, match))
                texts = [catalog.sources[k].get("text", "") for k in refs]
                if not any(texts):
                    fail("interpretation_source_not_text", path + ".citation_ids", "The selected source has no text for a qualitative interpretation.", item_index=index)
                if not isinstance(quote, str):
                    fail("interpretation_quote_type", path + ".quote", "The source excerpt must be a string.",
                         item_index=index, local_details=minimal_value(quote))
                if not 1 <= len(quote) <= 400:
                    fail("interpretation_quote_length", path + ".quote", "The source excerpt must contain 1-400 characters.",
                         item_index=index, max_characters=400, actual_characters=len(quote))
                if not any(quote in source for source in texts):
                    fail("interpretation_quote_not_literal", path + ".quote", "The proposed excerpt does not occur literally in the selected source text.",
                         item_index=index, local_details=minimal_value(quote))
                prefix = "Provisional interpretation for manager review: "
                excerpt = ' Source excerpt: "' + cell(quote) + '".'
            else:
                if quote is not None:
                    fail("proposal_quote", path + ".quote", "Proposals use quote=null and are not observed outcomes.", item_index=index)
                match = narrative_number(text, proposal=True)
                if match:
                    fail("numeric_proposal", path + ".text", "A digit or percentage keyword triggered the proposal rule; this alone does not establish an invented target. Select numeric facts separately.",
                         item_index=index, local_details=numeric_fragment(text, match))
                prefix, excerpt = "Proposed action for manager review (not an observed outcome): ", ""
            # Split model prose into individual review units, retaining its source anchor.
            units = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())
            for unit in units:
                rendered = prefix + unit + excerpt + " " + citations(refs)
                claims.append({"kind": "interpretation" if kind == "interpretations" else "proposal",
                    "text": rendered, "citation_ids": sorted(set(refs)), "scope": catalog.scope,
                    "quote": quote, "validation": "provisional_semantics"})
    if not claims:
        if catalog.facts:
            fail("answer_omitted_facts", "fact_ids", "Source facts are available; select the relevant facts instead of claiming missing evidence.")
        refs = sorted(catalog.sources)
        text = "No source-grounded claims were selected for release; this does not establish that relevant data is absent."
        if refs:
            text += " " + citations(refs)
        claims.append({"kind": "limitation", "text": text, "citation_ids": refs, "scope": catalog.scope,
                       "validation": "application_boundary"})
    elif any(c["kind"] in {"table", "observed", "calculated"} for c in claims):
        refs = sorted({k for c in claims for k in c["citation_ids"]})
        text = "These are scoped synthetic records, not causal effects or independently validated employee sentiment."
        if any(s.get("metric_id") == "survey_trend" for s in catalog.sources.values()):
            text += " Favorable survey ratings are 4 or 5 on the 1-5 scale; percentages use each row's response denominator."
        if any(s.get("kind") == "survey_sentiment" for s in catalog.sources.values()):
            text += " Sentiment labels are provisional and human validation is pending; counts describe comments, not employees."
        if any(s.get("metric_id") == "cross_team_contributions" for s in catalog.sources.values()):
            text += " Missing recognition records do not establish that recognition never occurred."
        if any("sql" in s and not s.get("metric_id") for s in catalog.sources.values()):
            text += " Exploratory query outputs still require review of metric meaning, grain and denominator."
        claims.append({"kind": "limitation", "text": text + " " + citations(refs),
                       "citation_ids": refs, "scope": catalog.scope, "validation": "application_boundary"})
    if len(claims) > 32:
        fail("claim_count", "answer", "Select at most 32 individual claims, including limitations.")
    for index, claim in enumerate(claims, 1):
        claim["finding_id"] = "F" + str(index)
    return "\n\n".join(c["text"] for c in claims), claims


def audit_claims(claims, answer, catalog, grounding=None):
    issues = []
    if not isinstance(claims, list) or not claims or len(claims) > 32 or any(not isinstance(c, dict) for c in claims):
        return ["Grounded answer requires a bounded list of individual claims."]
    if "\n\n".join(c.get("text", "") for c in claims) != answer:
        issues.append("Answer text differs from its source-bound claims.")
    try:
        if not grounding or grounding.get("version") != "source-facts-v1" or grounding.get("role") not in {"Original", "Cherry", "Vanilla"}:
            raise ValueError("Missing grounded answer contract.")
        expected_text, expected_claims = render_answer(grounding["payload"], catalog, grounding["role"])
        if answer != expected_text or claims != expected_claims:
            issues.append("Answer/claims differ from the controlled renderer output.")
    except (ValueError, KeyError, TypeError):
        issues.append("Grounded answer selection cannot be reproduced.")
    for index, claim in enumerate(claims, 1):
        if claim.get("finding_id") != "F" + str(index) or claim.get("scope") != catalog.scope:
            issues.append("Claim identity or scope is invalid.")
        kind = claim.get("kind")
        if not isinstance(kind, str):
            issues.append("Unknown claim type.")
            continue
        if kind in {"table", "observed", "calculated"}:
            key = claim.get("fact_id")
            fact = catalog.facts.get(key) if isinstance(key, str) else None
            if fact is None or any(claim.get(k) != v for k, v in fact.items()):
                issues.append("Numeric claim differs from recomputed source facts.")
        elif kind not in {"interpretation", "proposal", "limitation"}:
            issues.append("Unknown claim type.")
    return list(dict.fromkeys(issues))
