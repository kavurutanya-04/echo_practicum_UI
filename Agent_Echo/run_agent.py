"""Run one Echo role or the verified multi-agent workflow through Original."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys
import uuid

from agents import AccessScope, CherryAgent, VanillaAgent, OriginalAgent, ZeroSugarAgent, LimeAgent
from agents.preflight import check_connections
from agents.connections import DEFAULT_CONFIG, ModelRegistry
from agents.model import ConfigurationError, ScriptedDemoModel
from agents.runtime import RunBudget, AgentResult
from agents.execution_log import RunLog, record, error_summary, logged_model
from agents.capture import load_checkpoint, capture_summary, trace
from agents.resume import resume_phase

HERE = Path(__file__).resolve().parent
LOG_DIRECTORY = HERE / "reports" / "logs"
NAMES = {"cherry": "Cherry", "vanilla": "Vanilla", "original": "Original", "zerosugar": "ZeroSugar", "lime": "Lime", "visualizer": "Lime"}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", nargs="?", choices=tuple(NAMES))
    parser.add_argument("--manager", help="Demo manager scope; this is not authentication.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--question", help="Required in live mode; ignored by the scripted offline demo.")
    parser.add_argument("--input", type=Path, help="Existing JSON evidence artifact to review with ZeroSugar.")
    parser.add_argument("--resume", type=Path, help="Failed artifact or phase checkpoint; retry that phase only with live models.")
    parser.add_argument("--demo", action="store_true", help="Scripted offline integration; no credentials or API calls.")
    parser.add_argument("--connections", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile", help="Force one named model profile for every role in this run.")
    parser.add_argument("--show-connections", action="store_true", help="Show profile names and variable names, never credentials.")
    parser.add_argument("--check-connection", action="store_true", help="Make a real minimal tool call per selected profile; requires credentials.")
    parser.add_argument("--charts-dir", type=Path, help="Local SVG/CSV/metadata output directory for accepted charts.")
    parser.add_argument("--retrieval", choices=("lexical", "semantic", "hybrid"))
    parser.add_argument("--embedding-profile", help="Named embedding profile for semantic/hybrid retrieval.")
    parser.add_argument("--output", type=Path, help="Optional JSON evidence, trace and verification artifact.")
    parser.add_argument("--model-call-limit", type=int, default=32, help="Original/Vanilla model-call cap, 8-256; raise explicitly for a large sentiment corpus.")
    parser.add_argument("--run-seconds", type=int, default=300, help="Original/Vanilla elapsed-time cap, 30-3600 seconds.")
    args = parser.parse_args(argv)
    if not 8 <= args.model_call_limit <= 256 or not 30 <= args.run_seconds <= 3600:
        parser.error("Model-call limit must be 8-256 and run seconds 30-3600.")
    if (args.model_call_limit != 32 or args.run_seconds != 300) and args.agent not in {"original", "vanilla"} and not args.resume:
        parser.error("Budget overrides are supported for Original, Vanilla and phase resumption.")
    if args.resume and (args.demo or args.input or args.question or args.check_connection or args.show_connections):
        parser.error("--resume uses retained live inputs; do not combine it with --demo, --input, --question or connection checks.")
    if args.output and args.output.exists():
        print("Output already exists. Choose a fresh filename to preserve the previous execution.", file=sys.stderr)
        return 1
    if args.agent == "visualizer":
        args.agent = "lime"
    if args.show_connections and args.check_connection:
        parser.error("Choose --show-connections or --check-connection, not both.")
    if args.show_connections:
        return execute(args, parser)
    try:
        with RunLog(LOG_DIRECTORY, agent=args.agent, mode="offline_scripted_demo" if args.demo else "live",
                    connection_check=args.check_connection) as log:
            print("Execution log: " + str(log.path), flush=True)
            print("Full local capture: " + str(log.capture.directory), flush=True)
            code = execute(args, parser)
            log.finish(code)
            return code
    except OSError:
        print("Execution logging failed; check local reports/logs permissions and disk space.", file=sys.stderr)
        return 1
    except Exception:
        print("Unexpected execution failure; examine the execution log for the last completed step.", file=sys.stderr)
        return 1


def execute(args, parser):
    registry, agent = None, None
    declined_visual = None
    try:
        registry = ModelRegistry(args.connections, args.profile)
        saved = load_checkpoint(args.resume) if args.resume else None
        if saved:
            if args.agent and NAMES[args.agent] != saved['role']:
                raise ValueError('The requested role differs from the failed phase.')
            for field, value in (('manager', saved['scope']['manager_id']), ('start', saved['scope']['start_date']), ('end', saved['scope']['end_date'])):
                if getattr(args, field) and getattr(args, field) != value:
                    raise ValueError('Resume scope must exactly match the retained phase.')
                setattr(args, field, value)
            args.agent = saved['role'].lower()
            if args.profile is None and saved['payload'].get('profile'):
                registry.force_profile = saved['payload']['profile']
        if args.show_connections:
            print(json.dumps(registry.describe(), indent=2))
            return 0
        if args.check_connection:
            if args.demo:
                parser.error("--check-connection makes real API calls and cannot be combined with --demo.")
            roles = [NAMES[args.agent]] if args.agent else tuple(dict.fromkeys(NAMES.values()))
            print(json.dumps(check_connections(registry, roles,
                progress=lambda message: print(message, file=sys.stderr, flush=True)), indent=2))
            return 0
        if not args.agent or not args.manager:
            parser.error("An agent and --manager are required.")
        if args.agent in {"zerosugar", "lime"} and not args.input and not saved:
            parser.error("ZeroSugar/Lime require --input with a saved evidence artifact.")
        if args.agent not in {"zerosugar", "lime"} and not args.demo and not args.question and not saved:
            parser.error("--question is required in live mode.")
        artifact = json.loads(args.input.read_text(encoding="utf-8-sig")) if args.agent in {"zerosugar", "lime"} and not saved else None
        if artifact is not None and (not isinstance(artifact, dict) or
            not {"scope", "question", "answer", "evidence"}.issubset(artifact) or
            not isinstance(artifact["scope"], dict) or not isinstance(artifact["question"], str) or
            not isinstance(artifact["answer"], str) or not isinstance(artifact["evidence"], list)):
            raise ValueError("Input must be an Echo JSON artifact with scope, question, answer and evidence.")
        previous_scope = saved['scope'] if saved else artifact.get("scope", {}) if artifact else {}
        scope = AccessScope(args.manager, args.start or previous_scope.get("start_date", "2024-10-01"),
                            args.end or previous_scope.get("end_date", "2026-09-30"))
        record("scope_ready", **scope.__dict__)
        mode = "offline-scripted-demo" if args.demo else "live"
        print("MODE: OFFLINE SCRIPTED FIXTURE - 0 generation API calls; not a model evaluation."
              if args.demo else "MODE: LIVE - configured model API calls required; no offline fallback.")
        factory = (lambda name: logged_model(ScriptedDemoModel(name), name, "offline_fixture")) if args.demo else registry.get
        retrieval = args.retrieval or ("lexical" if args.demo else registry.config["retrieval"]["mode"])
        if args.demo and retrieval != "lexical":
            parser.error("Offline demos use lexical retrieval. Semantic/hybrid retrieval requires configured embeddings.")
        embedding_model = registry.embeddings(args.embedding_profile) if not saved and retrieval != "lexical" and args.agent in {"vanilla", "original"} else None
        options = {"retrieval": retrieval, "embedding_model": embedding_model, "cache_root": HERE / "data" / "rag_cache"}
        connections = {} if args.demo else registry.describe()
        trace('execution_configuration', connections=connections, arguments=vars(args),
              parent_run_id=saved['run_id'] if saved else None)
        if saved:
            result = resume_phase(saved, registry, HERE / 'data' / 'echo.db', args.model_call_limit, args.run_seconds)
        elif args.agent == "original":
            agent = OriginalAgent(HERE / "data" / "echo.db", scope, factory, mode, connections=connections,
                model_call_limit=args.model_call_limit, run_seconds=args.run_seconds, **options)
        elif args.agent == "cherry":
            agent = CherryAgent(HERE / "data" / "echo.db", scope, factory("Cherry"), mode)
        elif args.agent == "vanilla":
            agent = VanillaAgent(HERE / "data" / "echo.db", scope, factory("Vanilla"), mode,
                budget=RunBudget(model_limit=args.model_call_limit, tool_limit=48 + 2 * max(0, args.model_call_limit - 32),
                                 seconds=args.run_seconds), **options)
        elif args.agent == "zerosugar":
            agent = ZeroSugarAgent(scope, factory("ZeroSugar"), mode, database=HERE / "data" / "echo.db")
        else:
            if artifact["scope"] != scope.__dict__:
                raise ValueError("Input artifact scope differs from the requested scope.")
            if artifact.get("agent") != "Original":
                raise ValueError("Standalone Lime requires an Original workflow artifact.")
            if artifact.get("verification", {}).get("decision") != "accept":
                raise ValueError("Standalone Lime requires an accepted Original artifact; use Original to review specialist evidence first.")
            if artifact.get("status", "complete") not in {"complete", "unverified"}:
                raise ValueError("Standalone Lime requires a complete artifact, not a partial or failed analysis.")
            if not args.demo and artifact.get("mode") != "live":
                raise ValueError("A scripted demo artifact cannot be used as a live analytic result.")
            lime = LimeAgent(scope, factory("Lime"), mode)
            plan = lime.plan(artifact["question"], artifact["answer"], artifact["evidence"])
            artifact["visualization"] = asdict(plan)
            if plan.task_outcome and plan.task_outcome.get("status") == "declined":
                declined_visual = plan
            if not declined_visual:
                agent = ZeroSugarAgent(scope, factory("ZeroSugar"), mode, database=HERE / "data" / "echo.db")
        if saved:
            pass  # The isolated phase already ran; never enter Original's workflow.
        elif declined_visual:
            result = AgentResult("Lime", artifact["question"], declined_visual.reason, scope.__dict__,
                evidence=artifact["evidence"], mode=mode, status="declined", visualization=asdict(declined_visual),
                task_outcome=declined_visual.task_outcome)
        elif artifact and args.agent == "lime":
            result = agent.run(artifact)
            result.agent = "Lime"
            result.answer = artifact["answer"] if result.verification["decision"] == "accept" else "No verified visualization was produced; examine the review issues."
            result.visualization = artifact["visualization"] if result.verification["decision"] == "accept" else {
                "charts": [], "reason": "Chart plan was rejected; no files exported."}
        elif artifact:
            result = agent.run(artifact)
        else:
            examples = {"cherry": "Show quarterly recognition survey metrics.",
                        "vanilla": "Find anonymous survey examples about recognition.",
                        "original": "Review recognition using quarterly metrics and anonymous comments."}
            result = agent.run(examples[args.agent] if args.demo else args.question)
        result.connections = connections
        result.execution = {"generation_api_calls": 0, "successful_generation_api_calls": 0,
                            "note": "Scripted fixtures, not provider responses."} if args.demo else registry.execution_summary()
        result.capture = {**capture_summary(), **({'parent_run_id': saved['run_id'],
            'source_checkpoint': saved['source_path'], 'phase_only': True} if saved else {})}
        if result.visualization and result.verification.get("decision") == "accept" and result.status in {"complete", "unverified"}:
            directory = args.charts_dir or HERE / "reports" / "visuals" / uuid.uuid4().hex[:12]
            result.visualization["files"] = LimeAgent.export(result.visualization, result.evidence, scope, directory)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False), encoding="utf-8")
        if result.capture.get('resume_checkpoint'):
            print('Resume checkpoint: ' + result.capture['resume_checkpoint'])
        record("response_finished", status=result.status, supported_findings=sum(f["status"] == "supported" for f in result.findings),
               withheld_findings=sum(f["status"] != "supported" for f in result.findings))
        print("Result status: " + result.status)
        print(result.answer)
        print("Successful generation API calls: " + str(result.execution["successful_generation_api_calls"]))
        if result.rag.get("specialist_runs") or result.rag.get("retrieval_calls"):
            print("RAG trace: retrieval calls, returned source IDs and generation mode are stored in the JSON artifact.")
        if result.visualization:
            print("Lime: " + result.visualization["reason"])
            for files in result.visualization.get("files", []):
                print("Chart: " + files["svg"])
        if result.verification:
            review_status = result.verification.get("status", "completed")
            print("Verification: " + ("not run" if review_status == "not_run" else
                "failed to finish" if review_status == "failed" else result.verification["decision"]) +
                (" (scripted fixture, not LLM judgment)" if args.demo else ""))
        if args.output:
            print(f"Evidence artifact: {args.output.resolve()}")
        if result.status == "failed":
            return 1
        return 2 if result.status in {"partial", "needs_clarification", "declined", "incomplete"} or result.verification.get("decision") == "revise" else 0
    except KeyboardInterrupt:
        record("run_cancelled")
        print("Execution cancelled. API connectivity and answer quality were not confirmed by this interrupted run.", file=sys.stderr)
        return 130
    except (ConfigurationError, RuntimeError, ValueError, OSError, sqlite3.Error, KeyError) as error:
        record("run_error", **error_summary(error))
        print(str(error), file=sys.stderr)
        if args.output and args.agent:
            failure = getattr(error, "result", None) or AgentResult(NAMES[args.agent], args.question or "", "The analysis could not finish. No unverified findings are released.",
                {"manager_id": args.manager, "start_date": args.start, "end_date": args.end}, status="failed")
            failure.failure = error_summary(error)
            failure.status = "failed"
            failure.answer = "The analysis could not finish. Review the execution log for the failed step; no unverified findings are released."
            failure.execution = registry.execution_summary() if registry else {}
            failure.capture = {**capture_summary(), **({'source_artifact': str(args.resume), 'phase_only': True}
                if args.resume else {})}
            try:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(asdict(failure), indent=2, ensure_ascii=False), encoding="utf-8")
                print("Failure artifact: " + str(args.output.resolve()), file=sys.stderr)
            except OSError:
                print("Could not write the failure artifact; the execution log retains completed steps.", file=sys.stderr)
        return 1
    finally:
        if agent and hasattr(agent, "close"):
            agent.close()
        if registry:
            registry.close()


if __name__ == "__main__":
    sys.exit(main())
