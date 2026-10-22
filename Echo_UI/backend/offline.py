"""Offline demo answers: real numbers for the suggested questions, computed without any AI.

Each handler runs read-only SQL inside the manager's scope (the same team and date rules as Echo's
ScopedData), writes a short templated answer with [SQLn] citations, an optional chart spec, and
recomputes its headline numbers as a deterministic check. The wording is fixed templates, not model
output, and the UI says so.
"""

import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

SURVEY_MIN_RESPONSES = 5


def _key(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _quarter(iso):
    d = date.fromisoformat(iso)
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


def _signed(value, digits=2):
    return f"{value:+.{digits}f}"


class Query:
    """Runs scoped SQL and keeps a readable copy of each query as citable evidence."""

    def __init__(self, database, scope):
        self.db = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row
        self.scope = scope
        self.evidence = []
        self.extra = {}  # story fields: triangle, examples, watch, next_steps, voice
        self.team_filter = ("SELECT Employee_ID FROM HR_employees WHERE Pilot_Manager_ID = :manager "
                            "AND Hire_Date <= :end AND (Termination_Date IS NULL OR Termination_Date >= :start)")
        self.params = {"manager": scope.manager_id, "start": scope.start_date, "end": scope.end_date}
        self.teams = [r[0] for r in self.db.execute(
            f"SELECT DISTINCT Team_Display_Name FROM HR_employees WHERE Employee_ID IN ({self.team_filter})", self.params)]

    def run(self, sql, extra=None):
        params = {**self.params, **(extra or {})}
        rows = [dict(r) for r in self.db.execute(sql, params)]
        readable = sql
        for name, value in sorted(params.items(), key=lambda item: -len(item[0])):
            readable = readable.replace(f":{name}", f"'{value}'" if isinstance(value, str) else str(value))
        citation = f"SQL{len(self.evidence) + 1}"
        self.evidence.append({"citation_id": citation, "producer": "Cherry", "sql": " ".join(readable.split()),
                              "rows": rows, "truncated": False, "scope": self.scope.__dict__, "parameters": []})
        return citation, rows

    def team_in(self):
        return "(" + ",".join(f"'{t}'" for t in self.teams) + ")" if self.teams else "(NULL)"

    def close(self):
        self.db.close()


# ---------------------------------------------------------------- handlers
# Each returns (answer, findings, charts, limitations); findings are (text, [citations]).

def survey_trend(q, dimension="Recognition", last=None):
    cite, rows = q.run(f"""SELECT Survey_Date, Team, Responses, Mean_Score, Favorable_Percent FROM HR_survey_summary
        WHERE Dimension = :dim AND Team IN {q.team_in()} AND Survey_Date BETWEEN :start AND :end
        AND Responses >= {SURVEY_MIN_RESPONSES} ORDER BY Survey_Date""", {"dim": dimension})
    if last:
        dates = sorted({r["Survey_Date"] for r in rows})[-last:]
        rows = [r for r in rows if r["Survey_Date"] in dates]
        q.evidence[-1]["rows"] = rows
    return cite, rows


def recognition_trend(q):
    cite, rows = survey_trend(q)
    if not rows:
        return f"No Recognition survey results meet the minimum response count in this period [{cite}].", [], [], []
    if len(rows) == 1:
        only = rows[0]
        text = (f"This period has a single Recognition survey ({_quarter(only['Survey_Date'])}): {only['Mean_Score']:.2f} out of 5, "
                f"{only['Favorable_Percent']:.0f}% favorable from {only['Responses']} responses. Choose a longer period to see a trend.")
        return f"{text} [{cite}]", [(text, [cite])], [], []
    first, prev, latest = rows[0], rows[-2], rows[-1]
    high = max(rows, key=lambda r: r["Mean_Score"])
    low = min(rows, key=lambda r: r["Mean_Score"])
    direction = "up" if latest["Mean_Score"] > prev["Mean_Score"] else "down" if latest["Mean_Score"] < prev["Mean_Score"] else "flat"
    findings = [
        (f"Recognition was {latest['Mean_Score']:.2f} out of 5 in {_quarter(latest['Survey_Date'])} "
         f"({latest['Favorable_Percent']:.0f}% favorable, {latest['Responses']} responses), {direction} from "
         f"{prev['Mean_Score']:.2f} the quarter before.", [cite]),
        (f"Across the period it moved from {first['Mean_Score']:.2f} ({_quarter(first['Survey_Date'])}) to "
         f"{latest['Mean_Score']:.2f} ({_signed(latest['Mean_Score'] - first['Mean_Score'])}), ranging from "
         f"{low['Mean_Score']:.2f} in {_quarter(low['Survey_Date'])} to {high['Mean_Score']:.2f} in {_quarter(high['Survey_Date'])}.", [cite]),
    ]
    answer = " ".join(f"{text} [{c[0]}]" for text, c in findings)
    chart = {"source_id": cite, "kind": "line", "x": "Survey_Date", "y": "Mean_Score", "series": "Team",
             "title": "Recognition score by quarter", "x_label": "Survey date", "y_label": "Mean recognition score",
             "unit": "Score (1-5)", "denominator": "Responses"}
    limits = ["Survey scores are team averages for everyone surveyed in the team, which can include people outside your pilot roster.",
              "Quarter-to-quarter changes of a few tenths can reflect who responded, not a real change."]
    return answer, findings, [chart], limits


def recognition_eight_quarters(q):
    cite, rows = survey_trend(q, last=8)
    if not rows:
        return f"No Recognition survey results meet the minimum response count in this period [{cite}].", [], [], []
    if len(rows) == 1:
        only = rows[0]
        text = (f"This period contains one Recognition survey ({_quarter(only['Survey_Date'])}): {only['Favorable_Percent']:.0f}% favorable, "
                f"mean {only['Mean_Score']:.2f}. Choose \"All data\" to see eight quarters.")
        return f"{text} [{cite}]", [(text, [cite])], [], []
    favorable = [r["Favorable_Percent"] for r in rows]
    above4 = sum(r["Mean_Score"] >= 4 for r in rows)
    findings = [
        (f"Over the last {len(rows)} quarters in this period, Recognition favorability ranged from {min(favorable):.0f}% to "
         f"{max(favorable):.0f}%, and the mean score reached 4.0 or higher in {above4} of {len(rows)} quarters.", [cite]),
        (f"The latest quarter ({_quarter(rows[-1]['Survey_Date'])}) scored {rows[-1]['Mean_Score']:.2f} with "
         f"{rows[-1]['Favorable_Percent']:.0f}% favorable from {rows[-1]['Responses']} responses.", [cite]),
    ]
    answer = " ".join(f"{text} [{c[0]}]" for text, c in findings)
    chart = {"source_id": cite, "kind": "line", "x": "Survey_Date", "y": "Favorable_Percent", "series": "Team",
             "title": "Recognition favorability, last eight quarters", "x_label": "Survey date",
             "y_label": "Favorable responses", "unit": "%", "denominator": "Responses"}
    return answer, findings, [chart], ["Favorable % counts 4s and 5s; it is not the same metric as the mean score."]


def quarter_window(q):
    """The latest survey quarter inside the scope (three months ending on the latest survey date)."""
    latest = q.db.execute(f"""SELECT MAX(Survey_Date) FROM HR_survey_summary WHERE Team IN {q.team_in()}
        AND Survey_Date BETWEEN :start AND :end""", q.params).fetchone()[0]
    if not latest:
        return None, None
    end = date.fromisoformat(latest)
    start = (end.replace(day=1) - timedelta(days=62)).replace(day=1)
    return max(start.isoformat(), q.scope.start_date), latest


def this_quarter_recognition(q):
    start, end = quarter_window(q)
    if not end:
        return "There are no survey results in this period.", [], [], []
    c1, rows = q.run(f"""SELECT Survey_Date, Responses, Mean_Score, Favorable_Percent FROM HR_survey_summary
        WHERE Dimension = 'Recognition' AND Team IN {q.team_in()} AND Survey_Date <= :qend
        AND Survey_Date >= max(:start, date(:qend, '-6 months')) AND Responses >= {SURVEY_MIN_RESPONSES} ORDER BY Survey_Date""", {"qend": end})
    c2, work = q.run(f"""SELECT COUNT(*) AS Cross_Team_Contributions,
          SUM(EXISTS(SELECT 1 FROM HR_recognition_feedback f WHERE f.Contribution_ID = c.Contribution_ID
              AND f.Interaction_Type = 'Partner feedback')) AS With_Partner_Feedback,
          SUM(EXISTS(SELECT 1 FROM HR_recognition_feedback f WHERE f.Contribution_ID = c.Contribution_ID
              AND f.Interaction_Type = 'Manager recognition')) AS With_Manager_Recognition
        FROM OP_contributions c WHERE c.Employee_ID IN ({q.team_filter}) AND c.Home_Team <> c.Beneficiary_Team
        AND c.Contribution_Date BETWEEN :qstart AND :qend""", {"qstart": start, "qend": end})
    findings = []
    if rows:
        latest = rows[-1]
        text = (f"In {_quarter(latest['Survey_Date'])}, Recognition scored {latest['Mean_Score']:.2f} out of 5 "
                f"({latest['Favorable_Percent']:.0f}% favorable, {latest['Responses']} responses)")
        if len(rows) > 1:
            text += f", {_signed(latest['Mean_Score'] - rows[-2]['Mean_Score'])} versus the previous quarter"
        findings.append((text + ".", [c1]))
    w = work[0]
    total = w["Cross_Team_Contributions"] or 0
    if total:
        praised, recognized = w["With_Partner_Feedback"] or 0, w["With_Manager_Recognition"] or 0
        findings.append((f"The team made {total} contributions to other teams that quarter; {praised} "
                         f"({100 * praised / total:.0f}%) have recorded partner feedback and {recognized} "
                         f"({100 * recognized / total:.0f}%) have a recorded manager recognition.", [c2]))
        if rows and rows[-1]["Favorable_Percent"] >= 70 and recognized / total < 0.5:
            findings.append(("Survey sentiment and recorded recognition point in different directions: people "
                             "report feeling recognized, but much cross-team work has no recognition record.", [c1, c2]))
    answer = " ".join(f"{text} " + " ".join(f"[{c}]" for c in cites) for text, cites in findings)
    chart_rows = [{"Measure": "Cross-team contributions", "Count": total},
                  {"Measure": "With partner feedback", "Count": w["With_Partner_Feedback"] or 0},
                  {"Measure": "With manager recognition", "Count": w["With_Manager_Recognition"] or 0}]
    q.evidence.append({"citation_id": "SQL3", "producer": "Cherry", "sql": f"-- reshaped from {c2} for charting",
                       "rows": chart_rows, "truncated": False, "scope": q.scope.__dict__, "parameters": []})
    chart = {"source_id": "SQL3", "kind": "bar", "x": "Measure", "y": "Count", "title": "Cross-team work this quarter",
             "x_label": "Measure", "y_label": "Contributions", "unit": "contributions"}
    limits = ["Recognition records cover formal feedback only; other conversations may be unrecorded.",
              "A missing record is not proof that the work went unrecognized."]
    return answer, findings, [chart], limits


def over_capacity_weeks(q):
    cite, rows = q.run(f"""WITH demand AS (
            SELECT Assigned_Employee_ID AS e, Week_Start AS w, SUM(Current_Estimated_Hours) AS h FROM OP_work_requests
            WHERE Assigned_Employee_ID IN ({q.team_filter}) AND Week_Start BETWEEN :start AND :end GROUP BY 1, 2),
        cap AS (
            SELECT Employee_ID AS e, Week_Start AS w, Available_Project_Hours AS a FROM OP_capacity
            WHERE Employee_ID IN ({q.team_filter}) AND Week_Start BETWEEN :start AND :end AND Available_Project_Hours IS NOT NULL)
        SELECT d.w AS Week_Start, COUNT(*) AS People_With_Requests, SUM(d.h > c.a) AS People_Over_Capacity,
            ROUND(SUM(d.h), 1) AS Requested_Hours, ROUND(SUM(c.a), 1) AS Available_Hours
        FROM demand d JOIN cap c ON c.e = d.e AND c.w = d.w GROUP BY d.w ORDER BY d.w""")
    if not rows:
        return f"No weeks in this period have both requested and available hours recorded [{cite}].", [], [], []
    team_over = [r for r in rows if r["Requested_Hours"] > r["Available_Hours"]]
    any_over = [r for r in rows if r["People_Over_Capacity"]]
    worst = sorted(rows, key=lambda r: (-r["People_Over_Capacity"], r["Week_Start"]))[:3]
    findings = [
        (f"Across {len(rows)} weeks, the team as a whole was over its available project hours in {len(team_over)} week"
         f"{'' if len(team_over) == 1 else 's'}.", [cite]),
        (f"But individual overload is common: in {len(any_over)} of {len(rows)} weeks at least one person had more requested "
         f"hours than available hours, peaking at {worst[0]['People_Over_Capacity']} people in the week of {worst[0]['Week_Start']}.", [cite]),
        ("The busiest weeks were " + ", ".join(f"{r['Week_Start']} ({r['People_Over_Capacity']} people)" for r in worst)
         + ", which suggests work is unevenly spread rather than the team being short of hours.", [cite]),
    ]
    answer = " ".join(f"{text} [{c[0]}]" for text, c in findings)
    chart = {"source_id": cite, "kind": "bar", "x": "Week_Start", "y": "People_Over_Capacity",
             "title": "People with more requested than available hours, by week", "x_label": "Week starting",
             "y_label": "People over capacity", "unit": "people"}
    limits = ["Weeks where leave or routine hours were not recorded are excluded; missing is not zero.",
              "Requested hours are current estimates, not hours actually worked."]
    return answer, findings, [chart], limits


def contributions_without_recognition(q):
    cite, rows = q.run(f"""SELECT c.Beneficiary_Team AS Team_Helped, COUNT(*) AS Contributions,
          SUM(NOT EXISTS(SELECT 1 FROM HR_recognition_feedback f WHERE f.Contribution_ID = c.Contribution_ID
              AND f.Interaction_Type = 'Manager recognition')) AS Without_Recognition_Note
        FROM OP_contributions c WHERE c.Employee_ID IN ({q.team_filter}) AND c.Home_Team <> c.Beneficiary_Team
        AND c.Contribution_Date BETWEEN :start AND :end GROUP BY 1 ORDER BY Contributions DESC""")
    total = sum(r["Contributions"] for r in rows)
    if not total:
        return f"Your team recorded no cross-team contributions in this period [{cite}].", [], [], []
    missing = sum(r["Without_Recognition_Note"] for r in rows)
    top = rows[:3]
    findings = [
        (f"Of {total} contributions your team made to other teams, {missing} ({100 * missing / total:.0f}%) have no "
         f"recorded manager-recognition note.", [cite]),
        ("The teams helped most were " + ", ".join(f"{r['Team_Helped']} ({r['Contributions']}, {r['Without_Recognition_Note']} without a note)"
                                                   for r in top) + ".", [cite]),
    ]
    answer = " ".join(f"{text} [{c[0]}]" for text, c in findings)
    q.evidence[-1]["rows"] = rows[:12]
    chart = {"source_id": cite, "kind": "bar", "x": "Team_Helped", "y": "Without_Recognition_Note",
             "title": "Cross-team contributions without a recognition note", "x_label": "Team helped",
             "y_label": "Contributions without a note", "unit": "contributions"}
    limits = ["An absent note is not proof that recognition never happened; it may have been given informally.",
              "Chart shows the 12 teams helped most."]
    return answer, findings, [chart], limits


def biggest_survey_change(q):
    latest = q.db.execute(f"""SELECT MAX(Survey_Date) FROM HR_survey_summary WHERE Team IN {q.team_in()}
        AND Survey_Date BETWEEN :start AND :end""", q.params).fetchone()[0]
    if not latest:
        return "There are no survey results in this period.", [], [], []
    earlier = (date.fromisoformat(latest) - timedelta(days=370)).isoformat()
    cite, rows = q.run(f"""SELECT Dimension, Survey_Date, Mean_Score, Favorable_Percent, Responses FROM HR_survey_summary
        WHERE Team IN {q.team_in()} AND Dimension <> 'eNPS' AND Responses >= {SURVEY_MIN_RESPONSES}
        AND Survey_Date BETWEEN max(:start, :earlier) AND :latest ORDER BY Dimension, Survey_Date""",
        {"earlier": earlier, "latest": latest})
    by_dim = {}
    for r in rows:
        by_dim.setdefault(r["Dimension"], []).append(r)
    changes = [{"Dimension": d, "From": v[0]["Survey_Date"], "To": v[-1]["Survey_Date"],
                "Change": round(v[-1]["Mean_Score"] - v[0]["Mean_Score"], 2)} for d, v in by_dim.items() if len(v) >= 2]
    if not changes:
        return f"There is less than a year of comparable survey results in this period [{cite}].", [], [], []
    changes.sort(key=lambda c: c["Change"])
    up, down = changes[-1], changes[0]
    q.evidence.append({"citation_id": "SQL2", "producer": "Cherry", "sql": f"-- change per dimension computed from {cite}",
                       "rows": changes, "truncated": False, "scope": q.scope.__dict__, "parameters": []})
    findings = [
        (f"The biggest improvement was {up['Dimension']} ({_signed(up['Change'])} points between "
         f"{_quarter(up['From'])} and {_quarter(up['To'])}).", ["SQL2"]),
        (f"The biggest decline was {down['Dimension']} ({_signed(down['Change'])} points over the same window)." if down["Change"] < 0 else
         f"No area declined; the smallest gain was {down['Dimension']} ({_signed(down['Change'])} points).", ["SQL2"]),
    ]
    answer = " ".join(f"{text} [{c[0]}]" for text, c in findings)
    chart = {"source_id": "SQL2", "kind": "bar", "x": "Dimension", "y": "Change",
             "title": "Change in mean survey score over the last year", "x_label": "Survey area",
             "y_label": "Change in mean score", "unit": "points"}
    return answer, findings, [chart], ["Compares the first and last survey within the last 12 months of the period."]


def _tone(percent, good=70, fair=50):
    return "good" if percent >= good else "fair" if percent >= fair else "poor"


def invisible_work(q):
    """The project's anchor story: is help given to other teams seen and recognized?"""
    start, end = quarter_window(q)
    if not end:
        return "There are no survey results in this period to anchor a quarter.", [], [], []
    window = {"qstart": start, "qend": end}
    c1, work = q.run(f"""WITH c AS (
            SELECT c.Contribution_ID, c.Home_Team <> c.Beneficiary_Team AS cross_team,
              EXISTS(SELECT 1 FROM HR_recognition_feedback f WHERE f.Contribution_ID = c.Contribution_ID AND f.Interaction_Type = 'Partner feedback') AS praised,
              EXISTS(SELECT 1 FROM HR_recognition_feedback f WHERE f.Contribution_ID = c.Contribution_ID AND f.Interaction_Type = 'Partner feedback' AND f.Shared_With_Home_Manager = 'Yes') AS shared,
              EXISTS(SELECT 1 FROM HR_recognition_feedback f WHERE f.Contribution_ID = c.Contribution_ID AND f.Interaction_Type = 'Manager recognition') AS recognized
            FROM OP_contributions c WHERE c.Employee_ID IN ({q.team_filter}) AND c.Contribution_Date BETWEEN :qstart AND :qend)
        SELECT SUM(cross_team) AS Cross_Team, SUM(cross_team AND praised) AS Praised, SUM(cross_team AND shared) AS Praise_Shared_With_You,
          SUM(cross_team AND recognized) AS Recognized, SUM(cross_team AND praised AND NOT recognized) AS Praised_Not_Recognized,
          SUM(NOT cross_team) AS Own_Team, SUM(NOT cross_team AND recognized) AS Own_Team_Recognized FROM c""", window)
    c2, survey = q.run(f"""SELECT Survey_Date, Responses, Mean_Score, Favorable_Percent FROM HR_survey_summary
        WHERE Dimension = 'Recognition' AND Team IN {q.team_in()} AND Survey_Date = :qend AND Responses >= {SURVEY_MIN_RESPONSES}""", window)
    c3, voice = q.run(f"""SELECT COUNT(*) AS Responses, ROUND(100.0 * AVG(c.Response_Score >= 4)) AS Positive_Percent,
          ROUND(100.0 * AVG(c.Response_Score <= 2)) AS Negative_Percent
        FROM HR_survey_comments c JOIN HR_survey_summary s ON c.Survey_ID = s.Survey_ID
        WHERE c.Dimension = 'Recognition' AND c.Team IN {q.team_in()} AND c.Survey_Date = :qend AND s.Responses >= {SURVEY_MIN_RESPONSES}
        HAVING COUNT(*) >= {SURVEY_MIN_RESPONSES}""", window)
    c4, examples = q.run(f"""SELECT c.Contribution_ID, c.Employee_ID, c.Employee_Name, c.Beneficiary_Team AS Team_Helped, c.Contribution_Date,
          c.Business_Outcome, MAX(f.Shared_With_Home_Manager = 'Yes') AS Praise_Shared_With_You
        FROM OP_contributions c JOIN HR_recognition_feedback f ON f.Contribution_ID = c.Contribution_ID AND f.Interaction_Type = 'Partner feedback'
        WHERE c.Employee_ID IN ({q.team_filter}) AND c.Home_Team <> c.Beneficiary_Team AND c.Contribution_Date BETWEEN :qstart AND :qend
          AND NOT EXISTS(SELECT 1 FROM HR_recognition_feedback r WHERE r.Contribution_ID = c.Contribution_ID AND r.Interaction_Type = 'Manager recognition')
        GROUP BY c.Contribution_ID ORDER BY Praise_Shared_With_You DESC, c.Contribution_Date LIMIT 3""", window)
    w = work[0]
    total = w["Cross_Team"] or 0
    if not total:
        return f"Your team recorded no cross-team contributions in {_quarter(end)} [{c1}].", [], [], []
    recognized_pct = 100 * (w["Recognized"] or 0) / total
    own_pct = 100 * (w["Own_Team_Recognized"] or 0) / w["Own_Team"] if w["Own_Team"] else None
    praised = w["Praised"] or 0
    favorable = survey[0]["Favorable_Percent"] if survey else None
    findings = [
        (f"In {_quarter(end)} your team made {total} contributions to other teams; {praised} drew written praise from the team "
         f"they helped, but only {w['Recognized']} ({recognized_pct:.0f}%) were recognized by a manager.", [c1]),
    ]
    if own_pct is not None:
        findings.append((f"Work for your own team was recognized {own_pct:.0f}% of the time, so cross-team help is "
                         f"{'less' if recognized_pct < own_pct else 'not less'} likely to be recognized.", [c1]))
    if praised:
        findings.append((f"{w['Praised_Not_Recognized']} praised contributions have no recognition, and "
                         f"{w['Praise_Shared_With_You']} of the praise notes were sent to you.", [c1]))
    if favorable is not None:
        findings.append((f"Yet the team's Recognition survey is {favorable:.0f}% favorable "
                         f"({survey[0]['Mean_Score']:.2f} out of 5), so most people feel recognized overall.", [c2]))
    answer = " ".join(f"{text} [{c[0]}]" for text, c in findings)

    feedback_tone = _tone(recognized_pct, 50, 25)
    voice_tone = _tone(favorable) if favorable is not None else None
    conflict = voice_tone is not None and (voice_tone == "good") != (feedback_tone == "good")
    q.extra["triangle"] = {
        "work": {"value": str(total), "label": "contributions to other teams", "tone": "neutral", "agent": "Cherry"},
        "feedback": {"value": f"{recognized_pct:.0f}%", "label": "of that work recognized by a manager", "tone": feedback_tone, "agent": "Cherry"},
        "voice": {"value": f"{favorable:.0f}%" if favorable is not None else "n/a",
                  "label": "say recognition is good" if favorable is not None else "not enough survey responses",
                  "tone": voice_tone or "neutral", "agent": "Vanilla"},
        "agreement": "conflict" if conflict else "aligned",
        "note": ("The records and the survey disagree: people feel recognized overall, but most help given to other teams "
                 "has no recognition record. Both can be true: informal thanks may be unrecorded, or the people doing the "
                 "most cross-team work may be a minority of respondents.") if conflict else
                "The records and the survey point the same way.",
    }
    if voice:
        q.extra["voice"] = {"topic": "Recognition", "responses": voice[0]["Responses"],
                            "positive": voice[0]["Positive_Percent"], "negative": voice[0]["Negative_Percent"]}
    q.extra["examples"] = [{"contribution_id": e["Contribution_ID"], "employee_id": e["Employee_ID"], "name": e["Employee_Name"],
                            "team_helped": e["Team_Helped"], "date": e["Contribution_Date"], "outcome": e["Business_Outcome"],
                            "praise_reached_you": bool(e["Praise_Shared_With_You"])} for e in examples]
    q.extra["next_steps"] = [
        f"Start with the {w['Praise_Shared_With_You']} praise notes already sent to you: recognize the work specifically, naming the team it helped.",
        "Ask the managers your team helps most to copy you on partner feedback.",
        "Check again after next quarter's review using the measures below.",
    ]
    q.extra["watch"] = [
        {"metric": "Cross-team work recognized by a manager", "baseline": f"{recognized_pct:.0f}%", "goal": "above 50%"},
        {"metric": "Praised cross-team work left unrecognized", "baseline": str(w["Praised_Not_Recognized"]), "goal": "fewer each quarter"},
        {"metric": "Recognition survey favorable", "baseline": f"{favorable:.0f}%" if favorable is not None else "n/a", "goal": "hold steady"},
    ]
    chart_rows = [{"Stage": "Helped another team", "Contributions": total},
                  {"Stage": "Praised by that team", "Contributions": praised},
                  {"Stage": "Praise reached you", "Contributions": w["Praise_Shared_With_You"] or 0},
                  {"Stage": "Recognized by a manager", "Contributions": w["Recognized"] or 0}]
    q.evidence.append({"citation_id": f"SQL{len(q.evidence) + 1}", "producer": "Cherry", "sql": f"-- reshaped from {c1} for charting",
                       "rows": chart_rows, "truncated": False, "scope": q.scope.__dict__, "parameters": []})
    chart = {"source_id": q.evidence[-1]["citation_id"], "kind": "bar", "x": "Stage", "y": "Contributions",
             "title": f"Where cross-team work drops out of sight ({_quarter(end)})", "x_label": "Stage", "y_label": "Contributions",
             "unit": "contributions"}
    limits = ["Recognition records cover formal feedback logged at quarterly reviews; informal thanks may be unrecorded.",
              "The survey covers everyone surveyed in the team, which can include people outside your pilot roster.",
              "Use the examples to start a conversation, not to rate individuals."]
    return answer, findings, [chart], limits


GUARDRAIL = re.compile(r"\b(who (said|wrote|complained|posted|is unhappy|feels|thinks|answered)|which (employee|person|people|colleague)s? "
                       r"(said|wrote|complained|feel|answered)|identify|de-?anonymi[sz]e|name the (person|people|employee)|which comment)\b")


def guarded(question):
    return bool(GUARDRAIL.search(question.lower()))


def declined(scope, question):
    answer = ("Echo can't identify who wrote a survey response. Responses are anonymous by design, and using Echo to "
              "trace them back to people would break the trust the survey depends on. I can show what the team is saying "
              "as overall themes, or look at recorded work and feedback, which are not anonymous.")
    artifact = {"agent": "Original", "question": question, "answer": answer, "scope": scope.__dict__, "evidence": [],
                "mode": "offline-demo", "status": "declined", "verification": {"decision": "declined", "drafts_checked": 1},
                "delegations": [], "visualization": {"charts": []}, "rag": {}, "execution": {}, "sentiment": {}, "findings": [],
                "limitations": [], "next_steps": ["Open Team pulse to see themes from the survey without individual responses.",
                                                  "Ask \"Is my team's cross-team work being recognized?\" to look at recorded work instead."],
                "clarification_questions": [], "failure": {},
                "guardrail": {"rule": "No re-identification of anonymous survey responses",
                              "checked_by": "ZeroSugar", "detail": "Requests to find out who said something are declined before any data is read."}}
    return artifact, events(scope, 0, False, 0, declined=True)


HANDLERS = [
    ("cross team work being recognized", invisible_work),
    ("how is recognition trending", recognition_trend),
    ("this quarter s recognition metrics", this_quarter_recognition),
    ("recognition over eight quarters", recognition_eight_quarters),
    ("weeks exceed available project hours", over_capacity_weeks),
    ("contributions lack a recognition note", contributions_without_recognition),
    ("survey area changed most", biggest_survey_change),
]


def supported(question):
    key = _key(question)
    return next((handler for phrase, handler in HANDLERS if phrase in key), None)


def build(database, scope, question):
    """Returns (artifact, events) for a supported question, or None."""
    if guarded(question):
        return declined(scope, question)
    handler = supported(question)
    if handler is None:
        return None
    q = Query(database, scope)
    try:
        answer, findings, charts, limits = handler(q)
        # Deterministic check: replay each cited query as shown and confirm every cited row comes back.
        replay_ok = True
        for item in q.evidence:
            if item["sql"].startswith("--"):
                continue
            replayed = [dict(r) for r in q.db.execute(item["sql"])]
            replay_ok &= all(row in replayed for row in item["rows"])
    finally:
        q.close()
    finding_items = [{"finding_id": f"F{i + 1}", "text": text, "citation_ids": cites, "status": "supported",
                      "reason": "Numbers recomputed from the cited query.", "deterministic_issues": []}
                     for i, (text, cites) in enumerate(findings)]
    artifact = {
        "agent": "Original", "question": question, "answer": answer or "No answer.", "scope": scope.__dict__,
        "evidence": q.evidence, "tool_trace": [], "mode": "offline-demo", "status": "complete",
        "verification": {"decision": "accept" if replay_ok else "revise", "reviews": [], "drafts_checked": 1},
        "delegations": [{"agent": "Cherry", "question": question, "answer": "Ran scoped SQL for the requested metrics.",
                         "scope": scope.__dict__, "evidence": q.evidence}],
        "connections": {}, "visualization": {"charts": charts, "reason": "Chart chosen by a fixed offline rule." if charts else
                                              "No chart for this question.", "mode": "offline-demo", "tool_trace": [], "files": []},
        "rag": {}, "execution": {"generation_api_calls": 0, "successful_generation_api_calls": 0,
                                 "note": "Offline demo: templated answer computed from the data, no AI."},
        "sentiment": {}, "findings": finding_items, "limitations": limits, "next_steps": [],
        "clarification_questions": [], "failure": {}, "diagnostics": {},
    }
    artifact.update(q.extra)
    return artifact, events(scope, len([e for e in q.evidence if not e["sql"].startswith("--")]), bool(charts),
                            len(finding_items), voice="voice" in q.extra)


def unsupported(scope, question):
    answer = ("The offline demo can answer the suggested questions using your team's real data. "
              "For other questions, switch to Live AI.")
    artifact = {"agent": "Original", "question": question, "answer": answer, "scope": scope.__dict__, "evidence": [],
                "mode": "offline-demo", "status": "needs_clarification", "verification": {}, "delegations": [],
                "visualization": {"charts": []}, "rag": {}, "execution": {}, "sentiment": {}, "findings": [],
                "limitations": [], "next_steps": [], "clarification_questions": [], "failure": {}}
    return artifact, events(scope, 0, False, 0, plan_only=True)


def events(scope, queries, chart, findings, plan_only=False, voice=False, declined=False):
    """An execution log in Echo's format, so the agent strip lights up the same way as a live run."""
    run_id = "offline_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    clock = [0.0]
    log = []

    def add(event, step=0.4, **fields):
        clock[0] += step
        log.append({"time_utc": datetime.now(timezone.utc).isoformat(), "run_id": run_id,
                    "elapsed_seconds": round(clock[0], 2), "event": event, **fields})

    add("run_started", 0, agent="original", mode="offline_demo")
    add("scope_ready", **scope.__dict__)
    add("model_started", agent="Original", profile="offline_fixture")
    add("model_finished", agent="Original", profile="offline_fixture", tools=["submit_plan"])
    add("workflow_plan", agent="Original", needs_numbers=not (plan_only or declined), needs_text=voice, include_chart=chart,
        needs_clarification=plan_only)
    if declined:
        add("model_started", agent="ZeroSugar", profile="offline_fixture", step=0.6)
        add("model_finished", agent="ZeroSugar", profile="offline_fixture", tools=["submit_review"])
        add("verification_finished", agent="ZeroSugar", decision="declined", step=0.6)
        add("response_finished", status="declined")
        add("run_finished", status="declined")
        return log
    if plan_only:
        add("response_finished", status="needs_clarification")
        add("run_finished", status="needs_clarification")
        return log
    add("tool_started", agent="Original", tool="ask_cherry")
    add("agent_started", agent="Cherry")
    add("tool_started", agent="Cherry", tool="describe_schema")
    add("tool_finished", agent="Cherry", tool="describe_schema")
    for _ in range(max(1, queries)):
        add("tool_started", agent="Cherry", tool="execute_sql")
        add("tool_finished", agent="Cherry", tool="execute_sql", step=0.6)
    add("agent_finished", agent="Cherry")
    add("tool_finished", agent="Original", tool="ask_cherry")
    if voice:
        add("tool_started", agent="Original", tool="ask_vanilla")
        add("agent_started", agent="Vanilla")
        add("tool_started", agent="Vanilla", tool="summarize_voice", step=0.6)
        add("tool_finished", agent="Vanilla", tool="summarize_voice", step=0.9)
        add("agent_finished", agent="Vanilla")
        add("tool_finished", agent="Original", tool="ask_vanilla")
    add("model_started", agent="Original", profile="offline_fixture")
    add("model_finished", agent="Original", profile="offline_fixture", step=0.6)
    add("model_started", agent="Lime", profile="offline_fixture")
    add("model_finished", agent="Lime", profile="offline_fixture", tools=["submit_visuals"])
    add("visual_plan_validated", agent="Lime", charts=1 if chart else 0)
    add("model_started", agent="ZeroSugar", profile="offline_fixture")
    add("model_finished", agent="ZeroSugar", profile="offline_fixture", tools=["submit_review"])
    for i in range(findings):
        add("finding_reviewed", agent="ZeroSugar", finding_id=f"F{i + 1}", status="supported", step=0.3)
    add("verification_finished", agent="ZeroSugar", decision="accept")
    add("response_finished", status="complete")
    add("run_finished", status="complete")
    return log
