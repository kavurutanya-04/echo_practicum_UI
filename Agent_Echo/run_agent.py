"""Run one Echo role or the verified multi-agent workflow through Original."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from agents import AccessScope, CherryAgent, VanillaAgent, OriginalAgent, ZeroSugarAgent
from agents.connections import DEFAULT_CONFIG, ModelRegistry
from agents.model import ConfigurationError, ScriptedDemoModel

HERE = Path(__file__).resolve().parent
NAMES = {"cherry": "Cherry", "vanilla": "Vanilla", "original": "Original", "zerosugar": "ZeroSugar"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", nargs="?", choices=tuple(NAMES))
    parser.add_argument("--manager", help="Demo manager scope; this is not authentication.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--question", help="Required in live mode; ignored by the scripted offline demo.")
    parser.add_argument("--input", type=Path, help="Existing JSON evidence artifact to review with ZeroSugar.")
    parser.add_argument("--demo", action="store_true", help="Scripted offline integration; no credentials or API calls.")
    parser.add_argument("--connections", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile", help="Force one named model profile for every role in this run.")
    parser.add_argument("--show-connections", action="store_true", help="Show profile names and variable names, never credentials.")
    parser.add_argument("--retrieval", choices=("lexical", "semantic", "hybrid"))
    parser.add_argument("--embedding-profile", help="Named embedding profile for semantic/hybrid retrieval.")
    parser.add_argument("--output", type=Path, help="Optional JSON evidence, trace and verification artifact.")
    args = parser.parse_args()
    registry, agent = None, None
    try:
        registry = ModelRegistry(args.connections, args.profile)
        if args.show_connections:
            print(json.dumps(registry.describe(), indent=2))
            return 0
        if not args.agent or not args.manager:
            parser.error("An agent and --manager are required.")
        if args.agent == "zerosugar" and not args.input:
            parser.error("ZeroSugar requires --input with a saved evidence artifact.")
        if args.agent != "zerosugar" and not args.demo and not args.question:
            parser.error("--question is required in live mode.")
        artifact = json.loads(args.input.read_text(encoding="utf-8-sig")) if args.agent == "zerosugar" else None
        previous_scope = artifact.get("scope", {}) if artifact else {}
        scope = AccessScope(args.manager, args.start or previous_scope.get("start_date", "2024-10-01"),
                            args.end or previous_scope.get("end_date", "2026-09-30"))
        mode = "offline-scripted-demo" if args.demo else "live"
        factory = (lambda name: ScriptedDemoModel(name)) if args.demo else registry.get
        retrieval = args.retrieval or ("lexical" if args.demo else registry.config["retrieval"]["mode"])
        if args.demo and retrieval != "lexical":
            parser.error("Offline demos use lexical retrieval. Semantic/hybrid retrieval requires configured embeddings.")
        embedding_model = registry.embeddings(args.embedding_profile) if retrieval != "lexical" and args.agent in {"vanilla", "original"} else None
        options = {"retrieval": retrieval, "embedding_model": embedding_model, "cache_root": HERE / "data" / "rag_cache"}
        connections = {} if args.demo else registry.describe()
        if args.agent == "original":
            agent = OriginalAgent(HERE / "data" / "echo.db", scope, factory, mode, connections=connections, **options)
        elif args.agent == "cherry":
            agent = CherryAgent(HERE / "data" / "echo.db", scope, factory("Cherry"), mode)
        elif args.agent == "vanilla":
            agent = VanillaAgent(HERE / "data" / "echo.db", scope, factory("Vanilla"), mode, **options)
        else:
            agent = ZeroSugarAgent(scope, factory("ZeroSugar"), mode, database=HERE / "data" / "echo.db")
        if artifact:
            result = agent.run(artifact)
        else:
            examples = {"cherry": "Show quarterly recognition survey metrics.",
                        "vanilla": "Find anonymous survey examples about recognition.",
                        "original": "Review recognition using quarterly metrics and anonymous comments."}
            result = agent.run(examples[args.agent] if args.demo else args.question)
        result.connections = connections
        print(result.answer)
        if result.verification:
            print("Verification: " + result.verification["decision"] + (" (scripted fixture, not LLM judgment)" if args.demo else ""))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Evidence artifact: {args.output.resolve()}")
        return 2 if result.verification.get("decision") == "revise" else 0
    except (ConfigurationError, RuntimeError, ValueError, OSError, sqlite3.Error, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        if agent and hasattr(agent, "close"):
            agent.close()
        if registry:
            registry.close()


if __name__ == "__main__":
    sys.exit(main())
