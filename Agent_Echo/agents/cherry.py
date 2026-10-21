"""Cherry: model-generated Text-to-SQL over a restricted structured dataset."""

from .data_access import ScopedData
from .runtime import Specialist, function_tool
from .tools import SQLReader
from .metrics import MetricCatalog, METRICS


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
Worked patterns (use describe_schema to confirm exact columns first):
- "How many accepted cross-team contributions have no recorded manager recognition?"
  Count distinct Contribution_ID and use NOT EXISTS against recognition_feedback for
  the appropriate interaction type. Return total eligible contributions and missing-note
  count together; never join multiple feedback rows then count the expanded result.
- "Plot Recognition by quarter": select Team, Survey_Date, Responses, Mean_Score and
  Favorable_Percent from survey_summary for Dimension='Recognition'; order by date/team.
  Return numeric rows with units/denominators so Lime can chart them independently.
- "Which weeks exceed capacity?": pre-aggregate work_requests by assigned employee and
  Week_Start, then join capacity at that same grain. Separate routine and project hours.
- "Which benefit is least used?": use program_summary; explain eligible employee versus
  employee/offering record denominators. Do not expose individual participation history.
- "What caused low engagement?": describe associations and missing evidence, not causation.
Return the metric, period, population, exact numeric result, [SQLn] reference and limits.
For cross-team contribution counts, prefer run_metric(metric="cross_team_contributions",
dimension=null). It returns distinct totals and separate manager-recognition, partner-feedback
and no-feedback counts. State which definition answers the question; never equate these fields.
For a standard survey trend use run_metric(metric="survey_trend", dimension="Recognition")
or another exact dimension. For new questions generate SQL with execute_sql.
The data is already physically restricted to the caller's roster: manager_id is not an Employee_ID.
Stop querying once the requested metrics have been obtained. Respect the closing-turn instruction.
Prepared evidence may cover only part of the request. Compare its metric arguments with
ALL requested dimensions; use the available tools for missing metrics or custom calculations.
Use numeric_coverage as a task-status record, not proof that unqueried data does not exist.
Identical metric requests within this workflow reuse their original rows and citation ID.
Do not render charts or choose presentation layouts; those belong to Lime.
"""


class CherryAgent(Specialist):
    source_grounding = True
    def __init__(self, database, scope, model, mode="live", budget=None):
        backend = ScopedData(database, scope)
        try:
            self.reader = SQLReader(backend.structured_tables(), scope)
        finally:
            backend.close()
        tools = [
            function_tool("run_metric", "Run a validated metric on the authorized roster/period; prefer for standard counts or survey trends.", {
                "metric": {"type": "string", "enum": list(METRICS)},
                "dimension": {"type": ["string", "null"]}}),
            function_tool("describe_schema", "Inspect the permitted tables, columns and metric definitions.", {}),
            function_tool("execute_sql", "Execute one bounded read-only SQLite query on the scoped data copy.",
                          {"sql": {"type": "string", "description": "A SELECT query; WITH/CTEs are supported."}}),
        ]
        self.metric_cache = {}
        self.metric_errors = set()
        super().__init__("Cherry", INSTRUCTIONS, model, scope, tools,
            {"describe_schema": self.reader.describe, "execute_sql": self.reader.execute,
             "run_metric": self.run_metric}, mode, budget)

    def run_metric(self, metric, dimension=None):
        key = (metric, dimension.strip().casefold() if isinstance(dimension, str) else dimension)
        if key not in self.metric_cache:
            try:
                self.metric_cache[key] = MetricCatalog(self.reader).run(metric, dimension)
                self.metric_errors.discard(key)
            except (ValueError, TypeError):
                self.metric_errors.add(key)
                raise
        return self.metric_cache[key]

    def has_pending_work(self, evidence):
        return any(item["status"] in {"pending", "error"}
                   for item in self.numeric_coverage(evidence))

    def numeric_coverage(self, evidence):
        result = []
        for request in getattr(self, "required_metrics", []):
            matching = next((item for item in evidence if item.get("metric_id") == request["metric"]
                and str(item.get("metric_arguments", {}).get("dimension") or "").strip().casefold()
                == str(request["dimension"] or "").strip().casefold()), None)
            key = (request["metric"], request["dimension"].strip().casefold() if isinstance(request["dimension"], str) else None)
            if matching is None:
                status = "error" if key in getattr(self, "metric_errors", set()) else "pending"
            elif matching.get("truncated"):
                status = "error"
            else:
                status = "with_results" if matching.get("rows") else "no_rows"
            result.append({**request, "status": status,
                           "citation_id": matching.get("citation_id") if matching else None})
        return result

    def close(self):
        self.reader.close()
