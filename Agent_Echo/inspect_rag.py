"""Inspect real retrieval, separately from live answer generation."""

import argparse
import json
from pathlib import Path
import sys

from agents import AccessScope
from agents.connections import ModelRegistry
from agents.data_access import ScopedData
from agents.model import ConfigurationError
from agents.tools import TextSearch
from agents.semantic_search import SemanticTextSearch

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", required=True)
    parser.add_argument("--start", default="2026-07-01")
    parser.add_argument("--end", default="2026-09-30")
    parser.add_argument("--query", required=True)
    parser.add_argument("--retrieval", choices=("lexical", "semantic", "hybrid"), default="lexical")
    parser.add_argument("--embedding-profile")
    parser.add_argument("--source")
    parser.add_argument("--dimension")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    registry, searcher = ModelRegistry(), None
    try:
        scope = AccessScope(args.manager, args.start, args.end)
        backend = ScopedData(HERE / "data" / "echo.db", scope)
        try:
            documents = backend.text_documents()
        finally:
            backend.close()
        searcher = TextSearch(documents, scope) if args.retrieval == "lexical" else SemanticTextSearch(
            documents, scope, registry.embeddings(args.embedding_profile), HERE / "data" / "rag_cache", args.retrieval)
        result = searcher.search(args.query, args.source, args.dimension, args.limit)
        result["generation_performed"] = False
        result["note_generation"] = "Retrieval diagnostic only: no answer model or judge was called. Semantic/hybrid use embedding APIs."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0
    except (ConfigurationError, RuntimeError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        if searcher:
            searcher.close()
        registry.close()


if __name__ == "__main__":
    sys.exit(main())
