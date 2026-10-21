"""Offline source/provenance audit and human semantic-review packets for saved runs.

No model is invoked. A clean source replay is not a semantic accuracy score.
Generated packets contain local source text and must remain outside version control.
"""

import argparse
import json
from pathlib import Path

from agents.data_access import AccessScope, ScopedData
from agents.grounding import FactCatalog, audit_claims
from agents.tools import SQLReader
from agents.metrics import MetricCatalog
from agents.vanilla import validate_sentiment_labels
from agents.zero_sugar import ZeroSugarAgent

HERE = Path(__file__).resolve().parent


def audit_artifact(path, database=HERE / "data" / "echo.db"):
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    scope = AccessScope(**artifact["scope"])
    backend = ScopedData(database, scope)
    try:
        reader = SQLReader(backend.structured_tables(), scope)
        text_lookup = {doc["citation_id"]: doc for doc in backend.text_documents()}
        sentiment_documents = backend.sentiment_documents()
    finally:
        backend.close()
    output = {"artifact": str(Path(path).resolve()), "api_calls": 0,
        "semantic_quality": "human_review_required", "runs": [], "annotation_sample": [],
        "note": "Source checks do not establish query meaning, entailment or classifier accuracy. "
                "The annotation sample is for diagnostic review, not an unbiased performance estimate."}
    try:
        output["available_survey_dimensions"] = reader.describe()["survey_dimensions"]
        output["reference_survey_trends"] = {d: MetricCatalog(reader).run("survey_trend", d)["rows"]
                                              for d in output["available_survey_dimensions"]}
        for node in [artifact, *artifact.get("delegations", [])]:
            reports = node.get("sentiment", {})
            verifier = ZeroSugarAgent(scope, None, node.get("mode", "live"), sql_reader=reader,
                document_lookup=text_lookup, sentiment_reports=reports,
                sentiment_documents=sentiment_documents)
            evidence = node.get("evidence", [])
            candidate = "\n\n".join(c["text"] for c in node.get("claims", [])) or node.get("answer", "")
            issues = verifier.audit(candidate, evidence)
            contract = node.get("grounding", {}).get("version")
            catalog = FactCatalog(evidence, scope.__dict__)
            if contract:
                issues += audit_claims(node.get("claims", []), candidate, catalog, node["grounding"])
            else:
                issues.append("Legacy narrative has no reproducible claim-selection contract; audit prose manually.")
            output["runs"].append({"agent": node.get("agent"), "question": node.get("question"),
                "recorded_status": node.get("status"), "provenance_issues": list(dict.fromkeys(issues)),
                "available_facts": catalog.public(), "published_answer": node.get("answer", ""),
                "rejected_drafts": node.get("verification", {}).get("rejected_drafts", []),
                "semantic_review": {"status": "pending", "checks": [
                    "Does each assertion follow from its sources, including negation and quantifiers?",
                    "Are comparison dates, directions, units and denominators correct?",
                    "Does exploratory SQL answer the requested metric at the correct grain?",
                    "Are interpretation, uncertainty and proposed actions distinguished from observations?"]},
                "exploratory_queries": [e["sql"] for e in evidence if "sql" in e and not e.get("metric_id")]})
            if node.get("agent") == "Vanilla":
                output["runs"][-1]["text_interpretation_review"] = [
                    {"source_id": e["citation_id"], "source_text": e["text"],
                     "human_entailment_decision": None, "human_rationale": None}
                    for e in evidence if "text" in e][:20]
            lookup = {d["citation_id"]: d for d in sentiment_documents}
            for report in reports.values():
                documents = [d for d in sentiment_documents if report["dimension"] is None
                             or d["dimension"].casefold() == report["dimension"].casefold()]
                try:
                    validate_sentiment_labels(report["labels"], documents)
                except (ValueError, TypeError):
                    output["runs"][-1]["provenance_issues"].append("Sentiment labels failed local coverage/excerpt validation.")
                per_label = {}
                for item in report.get("labels", []):
                    identity, label = item.get("citation_id"), item.get("label")
                    if identity not in lookup or per_label.get(label, 0) >= 4:
                        continue
                    per_label[label] = per_label.get(label, 0) + 1
                    output["annotation_sample"].append({"agent": node.get("agent"), "source_id": identity,
                        "response_text": lookup[identity]["response_text"], "predicted_label": label,
                        "model_quote": item.get("quote"), "human_label": None, "human_rationale": None})
        if not output["annotation_sample"]:
            output["classification_quality"] = "not_assessable: no preserved classification labels in this artifact"
    finally:
        reader.close()
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True, help="Local JSON review packet, normally under reports/.")
    args = parser.parse_args()
    packets = [audit_artifact(path) for path in args.artifacts]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packets, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audited {len(packets)} artifacts; 0 API calls; semantic review remains pending.")
    print("Local review packet: " + str(args.output.resolve()))


if __name__ == "__main__":
    main()
