"""Run one fixed classroom-style evaluation case against actual configured APIs."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List case IDs without reading credentials or making requests.")
    parser.add_argument("--case", help="One ID from tests/evaluation_cases.json.")
    parser.add_argument("--profile")
    parser.add_argument("--retrieval", choices=("lexical", "semantic", "hybrid"), default="lexical")
    parser.add_argument("--embedding-profile")
    parser.add_argument("--output-dir", type=Path, default=HERE / "reports" / "live_evaluation")
    args = parser.parse_args()
    cases = json.loads((HERE / "tests" / "evaluation_cases.json").read_text(encoding="utf-8"))
    if args.list:
        print("\n".join(item["id"] for item in cases))
        return 0
    selected = next((item for item in cases if item["id"] == args.case), None)
    if selected is None:
        parser.error("Select an existing case with --case; use --list. This runner has no demo mode.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = selected["id"] + "_" + time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    artifact = args.output_dir / (stem + ".json")
    command = [sys.executable, str(HERE / "run_agent.py"), selected["agent"], "--manager", selected["manager"],
        "--start", selected["start"], "--end", selected["end"], "--question", selected["question"],
        "--retrieval", args.retrieval, "--output", str(artifact)]
    if args.profile:
        command += ["--profile", args.profile]
    if args.embedding_profile:
        command += ["--embedding-profile", args.embedding_profile]
    started = time.monotonic()
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                         env=os.environ | {"PYTHONUTF8": "1"})
    summary = {"case_id": selected["id"], "exit_code": run.returncode,
        "execution_log": next((line.removeprefix("Execution log: ") for line in run.stdout.splitlines()
                               if line.startswith("Execution log: ")), None),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "status": {0: "execution_completed", 2: "revision_required"}.get(run.returncode, "execution_failed"),
        "artifact": str(artifact) if artifact.exists() else None,
        "review_criteria": selected["review_criteria"], "human_quality_review": "pending",
        "note": "Review criteria were not sent to agents. Completion and model acceptance are not benchmark accuracy."}
    if artifact.exists():
        saved = json.loads(artifact.read_text(encoding="utf-8"))
        summary["response_status"] = saved.get("status", "unverified")
        summary["supported_findings"] = sum(f.get("status") == "supported" for f in saved.get("findings", []))
    summary_path = args.output_dir / (stem + "_review.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(run.stdout.strip())
    if run.stderr:
        print(run.stderr.strip(), file=sys.stderr)
    print("Human-review record: " + str(summary_path))
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
