"""Build physically scoped data copies before any model-generated query runs."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class AccessScope:
    """Trusted caller scope; a CLI manager selection is only a demo, not login."""

    manager_id: str
    start_date: str = "2024-10-01"
    end_date: str = "2026-09-30"

    def __post_init__(self):
        start, end = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
        if not date(2024, 10, 1) <= start <= end <= date(2026, 9, 30):
            raise ValueError("Scope must be within 2024-10-01 through 2026-09-30.")
        if not self.manager_id or len(self.manager_id) > 40:
            raise ValueError("A valid manager ID is required.")


def open_source(path):
    path = Path(path).resolve()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


class ScopedData:
    """Only this backend reads the full database; neither agent receives it."""

    def __init__(self, database, scope):
        self.source = open_source(database)
        self.scope = scope
        self.params = (scope.manager_id, scope.end_date, scope.start_date)
        self.employee_filter = """
            SELECT Employee_ID FROM HR_employees
            WHERE Pilot_Manager_ID = ? AND Hire_Date <= ?
              AND (Termination_Date IS NULL OR Termination_Date >= ?)
        """
        try:
            manager = self.source.execute(
                "SELECT Manager_ID, Manager_Name FROM HR_managers WHERE Manager_ID = ?",
                (scope.manager_id,),
            ).fetchone()
            if manager is None:
                raise ValueError("Unknown manager ID.")
            self.manager = dict(manager)
            self.teams = [row[0] for row in self.source.execute(
                f"SELECT DISTINCT Team_Display_Name FROM HR_employees WHERE Employee_ID IN ({self.employee_filter})",
                self.params,
            )]
        except Exception:
            self.source.close()
            raise

    def close(self):
        self.source.close()

    def employee_rows(self, table, employee_column, date_column=None, fields="*"):
        # Table/column identifiers here are developer constants, never model input.
        query = f"SELECT {fields} FROM {table} WHERE {employee_column} IN ({self.employee_filter})"
        params = self.params
        if date_column:
            query += f" AND {date_column} BETWEEN ? AND ?"
            params += (self.scope.start_date, self.scope.end_date)
        cursor = self.source.execute(query, params)
        return [col[0] for col in cursor.description], cursor.fetchall()

    def survey_rows(self, comments=False):
        placeholders = ",".join("?" for _ in self.teams) or "NULL"
        if comments:
            query = """SELECT c.Comment_ID, c.Survey_ID, c.Survey_Date, c.Department,
                c.Team, c.Dimension, c.Response_Score, c.Open_Text_Question, c.Response_Text
                FROM HR_survey_comments c JOIN HR_survey_summary s ON c.Survey_ID = s.Survey_ID
                WHERE c.Team IN ({}) AND c.Survey_Date BETWEEN ? AND ? AND s.Responses >= 5"""
        else:
            query = """SELECT * FROM HR_survey_summary WHERE Team IN ({})
                AND Survey_Date BETWEEN ? AND ? AND Responses >= 5"""
        cursor = self.source.execute(query.format(placeholders),
            (*self.teams, self.scope.start_date, self.scope.end_date))
        return [col[0] for col in cursor.description], cursor.fetchall()

    def structured_tables(self):
        """Approved fields only: no raw comments, tokens, contact details or QA."""
        tables = {}
        tables["employees"] = self.employee_rows(
            "HR_employees", "Employee_ID", fields="Employee_ID, Employee_Name, Department, Team_Display_Name, Job_Title, Job_Level, Hire_Date, Termination_Date")
        tables["survey_summary"] = self.survey_rows()
        for name, table, employee, event_date, fields in (
            ("contributions", "OP_contributions", "Employee_ID", "Contribution_Date",
             "Contribution_ID, Work_Request_ID, Employee_ID, Employee_Name, Home_Team, Beneficiary_Team, Contribution_Date"),
            ("recognition_feedback", "HR_recognition_feedback", "Employee_ID", "Interaction_Date",
             "Interaction_ID, Interaction_Type, Contribution_ID, Work_Request_ID, Employee_ID, Recipient_Manager_ID, Interaction_Date, Shared_With_Home_Manager, Record_Coverage"),
            ("capacity", "OP_capacity", "Employee_ID", "Week_Start", "*"),
            ("work_requests", "OP_work_requests", "Assigned_Employee_ID", "Week_Start",
             "Work_Request_ID, Project_ID, Project_Name, Requested_By_Manager_ID, Requesting_Team, Assigned_Employee_ID, Assigned_Employee_Name, Assigned_Employee_Team, Request_Date, Week_Start, Original_Due_Date, Current_Due_Date, Original_Priority, Current_Priority, Original_Estimated_Hours, Current_Estimated_Hours, Actual_Hours, Rework_Hours, Status, Work_Title, Completion_Date"),
        ):
            tables[name] = self.employee_rows(table, employee, event_date, fields)
        decision_query = f"""SELECT Decision_ID, Work_Request_ID, Related_Work_Request_ID,
            Decision_Date, Decision_Maker_ID, Decision_Type, Previous_Due_Date, Revised_Due_Date,
            Previous_Priority, Revised_Priority, Previous_Estimated_Hours, Revised_Estimated_Hours,
            Status_After_Decision FROM OP_priority_decisions
            WHERE Work_Request_ID IN (SELECT Work_Request_ID FROM OP_work_requests
                WHERE Assigned_Employee_ID IN ({self.employee_filter}))
              AND Decision_Date BETWEEN ? AND ?"""
        cursor = self.source.execute(decision_query,
            (*self.params, self.scope.start_date, self.scope.end_date))
        tables["priority_decisions"] = ([col[0] for col in cursor.description], cursor.fetchall())
        cursor = self.source.execute(f"""SELECT Project_ID, Project_Name, Sponsoring_Department,
            Sponsoring_Team, Project_Start_Date, Target_End_Date FROM OP_projects
            WHERE Project_ID IN (SELECT Project_ID FROM OP_work_requests
                WHERE Assigned_Employee_ID IN ({self.employee_filter}) AND Week_Start BETWEEN ? AND ?)""",
            (*self.params, self.scope.start_date, self.scope.end_date))
        tables["projects"] = ([col[0] for col in cursor.description], cursor.fetchall())
        # Participation is aggregated by team; no individual benefit-use history is exposed.
        cursor = self.source.execute(f"""SELECT Department, Team, Program_ID, Program_Type,
            Program_Name, Reporting_Period, Period_Start_Date, Period_End_Date,
            COUNT(*) AS Eligible_Records, COUNT(DISTINCT Employee_ID) AS Eligible_Employees,
            SUM(CASE WHEN Participation_Status IN ('Used','Completed','In progress') THEN 1 ELSE 0 END) AS Participating_Records,
            SUM(CASE WHEN Participation_Status = 'Completed' THEN 1 ELSE 0 END) AS Completed_Records,
            SUM(Use_Count) AS Total_Uses, SUM(Participation_Hours) AS Total_Participation_Hours,
            AVG(Usefulness_Score) AS Mean_Usefulness_Score
            FROM HR_program_participation WHERE Employee_ID IN ({self.employee_filter})
              AND Period_Start_Date <= ? AND Period_End_Date >= ?
            GROUP BY Department, Team, Program_ID, Program_Type, Program_Name,
                     Reporting_Period, Period_Start_Date, Period_End_Date
            HAVING COUNT(DISTINCT Employee_ID) >= 5""",
            (*self.params, self.scope.end_date, self.scope.start_date))
        tables["program_summary"] = ([col[0] for col in cursor.description], cursor.fetchall())
        return tables

    def sentiment_documents(self):
        """Full authorized responses without tokens, employee identity or numeric ratings."""
        _, rows = self.survey_rows(comments=True)
        return [{"citation_id": "survey:" + row["Comment_ID"], "source": "HR_survey_comments",
            "record_id": row["Comment_ID"], "team": row["Team"], "date": row["Survey_Date"],
            "dimension": row["Dimension"], "anonymous": True,
            "question": row["Open_Text_Question"] or "", "response_text": row["Response_Text"] or ""}
            for row in rows]

    def text_documents(self):
        """Every passage keeps its record ID, source, team, date and anonymity."""
        _, rows = self.survey_rows(comments=True)
        documents = []
        for row in rows:
            documents.append({
                "citation_id": "survey:" + row["Comment_ID"], "source": "HR_survey_comments",
                "record_id": row["Comment_ID"], "team": row["Team"],
                "date": row["Survey_Date"], "dimension": row["Dimension"],
                "anonymous": True, "text": row["Open_Text_Question"] + "\n" + row["Response_Text"],
            })
        for source, key, employee, event_date, team, text_columns in (
            ("HR_recognition_feedback", "Interaction_ID", "Employee_ID", "Interaction_Date", "Author_Team", ("Message",)),
            ("OP_contributions", "Contribution_ID", "Employee_ID", "Contribution_Date", "Home_Team", ("Project_Name", "Contribution_Summary", "Business_Outcome", "Evidence_Description")),
            ("OP_work_requests", "Work_Request_ID", "Assigned_Employee_ID", "Request_Date", "Assigned_Employee_Team", ("Project_Name", "Work_Title", "Work_Description", "Expected_Deliverable", "Dependency_Description")),
        ):
            _, rows = self.employee_rows(source, employee, event_date)
            for row in rows:
                documents.append({
                    "citation_id": source + ":" + row[key], "source": source,
                    "record_id": row[key], "team": row[team], "date": row[event_date],
                    "dimension": "", "anonymous": False,
                    "text": "\n".join(str(row[col]) for col in text_columns if row[col]),
                })
        cursor = self.source.execute(f"""SELECT d.*, w.Assigned_Employee_Team FROM OP_priority_decisions d
            JOIN OP_work_requests w ON d.Work_Request_ID = w.Work_Request_ID
            WHERE w.Assigned_Employee_ID IN ({self.employee_filter}) AND d.Decision_Date BETWEEN ? AND ?""",
            (*self.params, self.scope.start_date, self.scope.end_date))
        for row in cursor:
            documents.append({
                "citation_id": "OP_priority_decisions:" + row["Decision_ID"],
                "source": "OP_priority_decisions", "record_id": row["Decision_ID"],
                "team": row["Assigned_Employee_Team"], "date": row["Decision_Date"],
                "dimension": "", "anonymous": False,
                "text": "\n".join(str(row[col]) for col in ("Decision_Type", "Decision_Explanation", "Tradeoff") if row[col]),
            })
        return documents
