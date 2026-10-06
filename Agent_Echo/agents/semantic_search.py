"""Optional embedding/cosine retrieval aligned with the professor's RAG example."""

import hashlib
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3

from .tools import TextSearch
from .runtime import RunBudget


def normalized(vector):
    if not isinstance(vector, (list, tuple)) or not vector:
        raise ValueError("Embedding must be a nonempty numeric vector.")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in vector):
        raise ValueError("Embedding contains invalid values.")
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm or not math.isfinite(norm):
        raise ValueError("Embedding has an invalid norm.")
    return [value / norm for value in vector]


class SemanticTextSearch(TextSearch):
    def __init__(self, documents, scope, embedding_model, cache_root, mode="hybrid", budget=None):
        if mode not in {"semantic", "hybrid"}:
            raise ValueError("Semantic retrieval mode must be semantic or hybrid.")
        super().__init__(documents, scope)
        self.embedding_model, self.mode = embedding_model, mode
        self.budget = budget or RunBudget()
        texts = [document["text"][:6000] for document in documents]
        signature = json.dumps({"scope": scope.__dict__, "model": embedding_model.identity, "format": 1}, sort_keys=True)
        cache_path = Path(cache_root) / ("embeddings_" + hashlib.sha256(signature.encode()).hexdigest()[:24] + ".db")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        hashes = [hashlib.sha256(text.encode()).hexdigest() for text in texts]
        try:
            with closing(sqlite3.connect(cache_path)) as cache, cache:
                cache.execute("CREATE TABLE IF NOT EXISTS vectors (text_hash TEXT PRIMARY KEY, vector TEXT NOT NULL)")
                vectors = {key: normalized(json.loads(value)) for key, value in cache.execute("SELECT text_hash, vector FROM vectors")}
                pending = list(dict.fromkeys(key for key in hashes if key not in vectors))
                text_by_hash = dict(zip(hashes, texts))
                for start in range(0, len(pending), 24):
                    self.budget.consume("embedding")
                    batch = pending[start:start + 24]
                    generated = embedding_model.embed([text_by_hash[key] for key in batch])
                    if len(generated) != len(batch):
                        raise ValueError("Embedding response count does not match the input batch.")
                    for key, vector in zip(batch, generated):
                        vectors[key] = normalized(vector)
                        cache.execute("INSERT INTO vectors VALUES (?, ?)", (key, json.dumps(vectors[key])))
                    # Completed batches remain reusable if a later provider request fails.
                    cache.commit()
                self.vectors = [vectors[key] for key in hashes]
            self.dimensions = len(self.vectors[0]) if self.vectors else None
            if any(len(vector) != self.dimensions for vector in self.vectors):
                raise ValueError("Embedding dimensions are inconsistent; use a new model/profile cache.")
        except Exception:
            self.close()
            raise

    def search(self, query, source=None, dimension=None, limit=6):
        lexical = super().search(query, source, dimension, limit=12)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 12:
            raise ValueError("Search limit must be between 1 and 12.")
        if not query.strip() or not self.documents:
            return {"passages": [], "scope": self.scope.__dict__, "retrieval": self.mode,
                    "metadata": {"query": query, "returned_count": 0, "corpus_records": len(self.documents)},
                    "note": "No searchable query or scoped documents."}
        self.budget.consume("embedding")
        generated = self.embedding_model.embed([query])
        if len(generated) != 1:
            raise ValueError("Expected one query embedding.")
        query_vector = normalized(generated[0])
        if len(query_vector) != self.dimensions:
            raise ValueError("Query and document embedding dimensions differ.")
        candidates = []
        for index, (document, vector) in enumerate(zip(self.documents, self.vectors)):
            if source and document["source"] != source:
                continue
            if dimension and document["dimension"].lower() != dimension.lower():
                continue
            score = sum(a * b for a, b in zip(vector, query_vector))
            candidates.append((score, index))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        semantic_ranks = {self.documents[index]["citation_id"]: rank for rank, (_, index) in enumerate(candidates, 1)}
        lexical_ranks = {doc["citation_id"]: rank for rank, doc in enumerate(lexical["passages"], 1)}
        if self.mode == "hybrid":
            candidates.sort(key=lambda item: -(
                1 / (60 + semantic_ranks[self.documents[item[1]]["citation_id"]]) +
                (1 / (60 + lexical_ranks[self.documents[item[1]]["citation_id"]])
                 if self.documents[item[1]]["citation_id"] in lexical_ranks else 0)))
        hits, seen = [], set()
        for score, index in candidates:
            document = self.documents[index]
            key = (document["source"], document["text"].strip().lower())
            if key in seen:
                continue
            seen.add(key)
            hit = {**document, "text": document["text"][:1600],
                   "text_truncated": len(document["text"]) > 1600, "cosine_similarity": round(score, 6)}
            hits.append(hit)
            if len(hits) == limit:
                break
        return {"passages": hits, "scope": self.scope.__dict__,
                "retrieval": self.mode + " local retrieval with provider embeddings and cosine similarity",
                "metadata": {"query": query, "source_filter": source, "dimension_filter": dimension,
                    "requested_limit": limit, "corpus_records": len(self.documents), "returned_count": len(hits),
                    "embedding_identity": self.embedding_model.identity,
                    "ranking": "reciprocal rank fusion (k=60)" if self.mode == "hybrid" else "cosine similarity"},
                "note": "Similarity is a retrieval score, not confidence or prevalence. Passages are selected examples."}
