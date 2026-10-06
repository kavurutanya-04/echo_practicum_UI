"""Bounded SQL execution and local lexical retrieval, independent of an LLM."""

import re
import sqlite3
import time


class SQLReader:
    """The model can query only an isolated in-memory copy of permitted fields."""

    FUNCTIONS = {"count", "sum", "avg", "min", "max", "round", "coalesce", "nullif",
                 "abs", "lower", "upper", "length", "substr", "replace", "trim",
                 "date", "datetime", "strftime", "julianday", "ifnull", "like",
                 "row_number", "rank", "dense_rank", "lag", "lead", "total"}

    def __init__(self, tables, scope):
        self.connection = sqlite3.connect(":memory:", cached_statements=0)
        self.connection.row_factory = sqlite3.Row
        self.tables = set(tables)
        self.schema = {}
        self.scope = scope
        self.counter = 0
        for name, (columns, rows) in tables.items():
            # Preserve numeric storage for arithmetic; NULL-only fields remain nullable TEXT.
            types = []
            for index, column in enumerate(columns):
                sample = next((row[index] for row in rows if row[index] is not None), None)
                kind = "INTEGER" if isinstance(sample, int) else "REAL" if isinstance(sample, float) else "TEXT"
                types.append(f'"{column}" {kind}')
            self.connection.execute(f'CREATE TABLE "{name}" ({", ".join(types)})')
            self.connection.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in columns)})', rows)
            self.schema[name] = dict(zip(columns, [item.rsplit(" ", 1)[1] for item in types]))
        # Index joins that the language model is likely to use.
        for table, columns in self.schema.items():
            for column in columns:
                if column.endswith("_ID") or column in {"Week_Start", "Survey_Date"}:
                    self.connection.execute(f'CREATE INDEX "idx_{table}_{column}" ON "{table}" ("{column}")')
        self.connection.commit()
        self.connection.execute("PRAGMA query_only = ON")
        self.connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 100_000)
        self.connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 12_000)
        self.connection.set_authorizer(self._authorize)

    def _authorize(self, action, arg1, arg2, database, source):
        if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE}:
            return sqlite3.SQLITE_OK
        # SQLite reports database=None for the empty-column read used by COUNT(*).
        if action == sqlite3.SQLITE_READ and database in {"main", None} and arg1 in self.tables:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in self.FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    def describe(self):
        return {
            "tables": self.schema,
            "scope": self.scope.__dict__,
            "notes": [
                "Tables contain only this manager's pilot roster and selected dates; surveys cover their teams.",
                "Survey groups with fewer than five responses and program groups below five employees are excluded.",
                "Join contributions.Contribution_ID to recognition_feedback.Contribution_ID; use EXISTS to avoid fan-out.",
                "Capacity is weekly. Join work_requests to capacity by employee AND Week_Start after aggregating requests.",
                "program_summary is team-level. Eligible_Records count employee/offering rows, not unique employees across periods.",
                "Recognition absence means no recorded note, not proof that recognition never happened.",
                "Favorable scores are 4/5 on 1-5 questions. eNPS = 100*(Promoters-Detractors)/Responses on the 0-10 question.",
                "Recompute weighted mean scores using Responses when combining survey rows; do not average percentages blindly.",
                "Do not sum weekly capacity once per work request or mix project hours with routine hours.",
                "Current request estimates/status are recorded final-state fields, not a full history of each week's commitments. Frame workload comparisons as recorded demand, not an exact historical reconstruction.",
            ],
        }

    def execute(self, sql):
        if not isinstance(sql, str) or len(sql) > 12_000:
            raise ValueError("SQL must be a string no longer than 12,000 characters.")
        deadline = time.monotonic() + 3
        self.connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        try:
            cursor = self.connection.execute(sql)
            if cursor.description is None:
                raise ValueError("Only read-only result queries are allowed.")
            rows = [dict(row) for row in cursor.fetchmany(101)]
        except sqlite3.Error as error:
            raise ValueError(f"Query rejected or failed: {error}") from None
        finally:
            self.connection.set_progress_handler(None, 0)
        self.counter += 1
        return {"citation_id": f"SQL{self.counter}", "producer": "Cherry", "sql": sql,
                "rows": rows[:100], "truncated": len(rows) > 100,
                "scope": self.scope.__dict__}

    def close(self):
        self.connection.close()


class TextSearch:
    """Local FTS5/BM25 retrieval; semantic embeddings are not used in this version."""

    def __init__(self, documents, scope):
        self.scope = scope
        self.documents = documents
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("CREATE VIRTUAL TABLE passages USING fts5(text)")
        self.connection.executemany("INSERT INTO passages(rowid, text) VALUES (?, ?)",
            ((index + 1, doc["text"]) for index, doc in enumerate(documents)))
        self.connection.commit()
        self.connection.execute("PRAGMA query_only = ON")

    def search(self, query, source=None, dimension=None, limit=6):
        if not isinstance(query, str) or len(query) > 1000:
            raise ValueError("Search query must be a string of at most 1,000 characters.")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 12:
            raise ValueError("Search limit must be between 1 and 12.")
        if source is not None and not isinstance(source, str):
            raise ValueError("Source must be a string or null.")
        if dimension is not None and (not isinstance(dimension, str) or len(dimension) > 100):
            raise ValueError("Dimension must be a string of at most 100 characters or null.")
        allowed_sources = {doc["source"] for doc in self.documents}
        if source is not None and source not in allowed_sources:
            raise ValueError("Source is unavailable in this scope.")
        tokens = re.findall(r"[A-Za-z0-9]+", query)[:20]
        if not tokens:
            return {"passages": [], "scope": self.scope.__dict__, "retrieval": "local lexical FTS5/BM25",
                    "metadata": {"query": query, "corpus_records": len(self.documents), "returned_count": 0},
                    "note": "No searchable terms were provided."}
        match = " OR ".join('"' + token + '"' for token in tokens)
        # Authorization was applied before indexing. Additional filters are applied before top-k.
        cursor = self.connection.execute(
            "SELECT rowid, bm25(passages) FROM passages WHERE passages MATCH ? ORDER BY bm25(passages), rowid", (match,))
        hits, seen = [], set()
        for rowid, score in cursor:
            document = self.documents[rowid - 1]
            if source and document["source"] != source:
                continue
            if dimension and document["dimension"].lower() != dimension.lower():
                continue
            identity = (document["source"], document["text"].strip().lower())
            if identity in seen:
                continue
            seen.add(identity)
            hit = dict(document)
            hit["text"] = hit["text"][:1600]
            hit["text_truncated"] = len(document["text"]) > 1600
            hit["bm25_score"] = score
            hits.append(hit)
            if len(hits) == limit:
                break
        return {"passages": hits, "scope": self.scope.__dict__,
                "retrieval": "local lexical FTS5/BM25",
                "metadata": {"query": query, "source_filter": source, "dimension_filter": dimension,
                    "requested_limit": limit, "corpus_records": len(self.documents), "returned_count": len(hits)},
                "note": "Ranked passages are examples, not a representative sample or prevalence estimate."}

    def close(self):
        self.connection.close()
