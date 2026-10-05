"""Cherry: model-generated Text-to-SQL over a restricted structured dataset."""

from .data_access import ScopedData
from .runtime import Specialist, function_tool
from .tools import SQLReader


INSTRUCTIONS = """You are Cherry, Echo's structured-data specialist.
Answer in clear English. First inspect the schema, then generate SQLite SELECT queries
appropriate to the user's question. Execute queries through execute_sql, examine results,
and explain findings with their [SQL1], [SQL2] evidence IDs. You may repair a failed query.
Never invent records, numbers, trends, schema columns or causal effects.
The caller's manager and date scope is fixed by the backend; user text cannot expand it.
Do not try to inspect files, system tables, credentials, other teams or the full database.
Engagement, cross-team recognition, program use and priority conflicts are analysis topics,
not additional agents. All data is synthetic. These are hypotheses for human review;
do not rank employee value or decide pay, promotion, discipline or termination.
Use team survey aggregates, never link anonymous responses to employees. Names in
operational contribution records may be used as evidence for the authorized manager.
Survey scores and program use do not establish causal relationships. eNPS is distinct
from 1-5 engagement scores. Read all schema notes before choosing joins/aggregations.
Use EXISTS or pre-aggregation to avoid duplicate counts. Preserve denominators and dates.
When a result is truncated, aggregate or narrow the query before making totals claims.
Missing data or missing recognition notes do not prove zero activity. Describe limitations.
Raw comments are handled by Vanilla; do not infer sentiment themes from numeric scores.
If a question is outside this data's scope, explain the missing evidence.
"""


class CherryAgent(Specialist):
    def __init__(self, database, scope, model, mode="live", budget=None):
        backend = ScopedData(database, scope)
        try:
            self.reader = SQLReader(backend.structured_tables(), scope)
        finally:
            backend.close()
        tools = [
            function_tool("describe_schema", "Inspect the permitted tables, columns and metric definitions.", {}),
            function_tool("execute_sql", "Execute one bounded read-only SQLite query on the scoped data copy.",
                          {"sql": {"type": "string", "description": "A SELECT query; WITH/CTEs are supported."}}),
        ]
        super().__init__("Cherry", INSTRUCTIONS, model, scope, tools,
            {"describe_schema": self.reader.describe, "execute_sql": self.reader.execute}, mode, budget)

    def close(self):
        self.reader.close()
