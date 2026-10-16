"""Versioned, read-only metrics over the existing physically scoped SQL copy."""

from .execution_log import record

METRICS = ("cross_team_contributions", "survey_trend")


class MetricCatalog:
    def __init__(self, reader, actor="Cherry"):
        self.reader = reader
        self.actor = actor

    def run(self, metric, dimension=None):
        if metric not in METRICS:
            raise ValueError("Unknown metric. Use cross_team_contributions or survey_trend.")
        version = 1
        if metric == "cross_team_contributions":
            if isinstance(dimension, str) and dimension.strip().casefold() in {"none", "null", "n/a", ""}:
                dimension = None
            if dimension is not None:
                raise ValueError("Cross-team contribution metrics require dimension=null.")
            sql = """WITH eligible AS (
                SELECT DISTINCT Contribution_ID FROM contributions
                WHERE Home_Team <> Beneficiary_Team
            ), flags AS (
                SELECT c.Contribution_ID,
                  EXISTS(SELECT 1 FROM recognition_feedback f WHERE f.Contribution_ID=c.Contribution_ID
                    AND f.Interaction_Type='Manager recognition') AS manager_note,
                  EXISTS(SELECT 1 FROM recognition_feedback f WHERE f.Contribution_ID=c.Contribution_ID
                    AND f.Interaction_Type='Partner feedback') AS partner_note,
                  EXISTS(SELECT 1 FROM recognition_feedback f WHERE f.Contribution_ID=c.Contribution_ID) AS any_note
                FROM eligible c
            ) SELECT COUNT(*) AS Total_Contributions,
                COALESCE(SUM(manager_note),0) AS With_Manager_Recognition,
                COALESCE(SUM(1-manager_note),0) AS Without_Manager_Recognition,
                COALESCE(SUM(partner_note),0) AS With_Partner_Feedback,
                COALESCE(SUM(1-any_note),0) AS Without_Any_Feedback FROM flags"""
            parameters = []
            definition = ("Distinct cross-team Contribution_ID in the authorized roster and contribution period. "
                "Manager recognition, partner feedback and absence of any feedback are separate counts. "
                "Feedback is restricted to the selected interaction period; missing notes do not prove "
                "absent recognition or unfair treatment. Recorded coverage may be incomplete.")
        else:
            if not isinstance(dimension, str) or not 1 <= len(dimension.strip()) <= 100:
                raise ValueError("survey_trend requires one exact survey dimension.")
            version = 2
            dimension = dimension.strip()
            sql = """SELECT Team, Survey_Date, Responses, Mean_Score, Favorable_Percent
                FROM survey_summary WHERE Dimension = ? COLLATE NOCASE ORDER BY Survey_Date, Team"""
            parameters = [dimension]
            definition = ("Recorded team/date survey aggregates for the exact dimension, preserving Responses "
                          "as denominator. Dimension matching ignores letter case and surrounding input whitespace, "
                          "without fuzzy or partial matching. Rows are not employee-level sentiment labels or causal effects.")
        result = self.reader.execute(sql, parameters)
        result.update(metric_id=metric, metric_version=version, metric_arguments={"dimension": dimension},
                      metric_definition=definition)
        record("metric_replayed" if self.actor == "ZeroSugar" else "metric_executed", agent=self.actor, metric_id=metric, metric_version=version,
               rows=len(result["rows"]), truncated=result["truncated"])
        return result
