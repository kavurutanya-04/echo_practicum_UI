"""Create an evidence-based, read-only quarterly recognition report for a manager."""
import argparse
from calendar import monthrange
from datetime import date
from pathlib import Path
import re
import sqlite3
import sys

HERE = Path(__file__).resolve().parent


def quarter_dates(quarter):
    match = re.fullmatch(r'(\d{4})-Q([1-4])', quarter)
    if not match:
        raise ValueError('Use a quarter such as 2026-Q3.')
    year, number = map(int, match.groups())
    start_month = (number - 1) * 3 + 1
    end_month = number * 3
    return date(year, start_month, 1).isoformat(), date(year, end_month, monthrange(year, end_month)[1]).isoformat()


def get_recognition_report(database, manager_id, quarter, limit=10):
    """Demo manager selection is not authentication; caller checks come later."""
    if not 1 <= limit <= 50:
        raise ValueError('The evidence sample limit must be between 1 and 50.')
    start, end = quarter_dates(quarter)
    uri = Path(database).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA query_only = ON')
        row = connection.execute('SELECT Manager_ID, Manager_Name, Primary_Team, Primary_Department, Coverage_Start_Date, Coverage_End_Date FROM HR_managers WHERE Manager_ID = ?', (manager_id,)).fetchone()
        if row is None:
            raise ValueError('Manager ID is not present in the pilot roster.')
        manager = dict(row)
        if start < manager['Coverage_Start_Date'] or end > manager['Coverage_End_Date']:
            raise ValueError(f'Choose a quarter inside {manager["Coverage_Start_Date"]} through {manager["Coverage_End_Date"]}.')
        rows = connection.execute('''
            SELECT c.Contribution_ID, c.Work_Request_ID, c.Project_Name,
                   c.Employee_ID, c.Employee_Name, c.Home_Team, c.Beneficiary_Team,
                   c.Contribution_Date, c.Contribution_Summary, c.Business_Outcome,
                   c.Evidence_Description,
                   EXISTS(SELECT 1 FROM HR_recognition_feedback f
                          WHERE f.Contribution_ID=c.Contribution_ID
                            AND f.Interaction_Type='Manager recognition') AS Has_Manager_Recognition,
                   EXISTS(SELECT 1 FROM HR_recognition_feedback f
                          WHERE f.Contribution_ID=c.Contribution_ID
                            AND f.Interaction_Type='Partner feedback') AS Has_Partner_Feedback,
                   EXISTS(SELECT 1 FROM HR_recognition_feedback f
                          WHERE f.Contribution_ID=c.Contribution_ID
                            AND f.Interaction_Type='Partner feedback'
                            AND f.Shared_With_Home_Manager='Yes') AS Partner_Feedback_Shared
            FROM OP_contributions c
            JOIN HR_employees e ON e.Employee_ID=c.Employee_ID
            WHERE e.Pilot_Manager_ID=?
              AND c.Contribution_Date BETWEEN ? AND ?
              AND c.Home_Team<>c.Beneficiary_Team
            ORDER BY c.Contribution_Date DESC, c.Contribution_ID
        ''', (manager_id, start, end)).fetchall()
        contributions = [dict(row) for row in rows]
        employee_rows = connection.execute('SELECT Employee_ID, Employee_Name FROM HR_employees WHERE Pilot_Manager_ID=? AND Hire_Date<=? AND (Termination_Date IS NULL OR Termination_Date>=?) ORDER BY Employee_Name', (manager_id, end, start)).fetchall()
        employees = {row['Employee_ID']: dict(row, Contributions=0, Contributions_With_Manager_Recognition=0, Contributions_With_Partner_Feedback=0, Contributions_Without_Manager_Recognition=0) for row in employee_rows}
        for item in contributions:
            employee = employees[item['Employee_ID']]
            employee['Contributions'] += 1
            employee['Contributions_With_Manager_Recognition'] += item['Has_Manager_Recognition']
            employee['Contributions_With_Partner_Feedback'] += item['Has_Partner_Feedback']
            employee['Contributions_Without_Manager_Recognition'] += not item['Has_Manager_Recognition']
        missing = [item for item in contributions if not item['Has_Manager_Recognition']]
        # Selection is by available evidence and recency, never an employee score.
        missing.sort(key=lambda item: (-item['Has_Partner_Feedback'], -date.fromisoformat(item['Contribution_Date']).toordinal(), item['Contribution_ID']))
        sample = missing[:limit]
        for item in sample:
            item['Recorded_Interactions'] = [dict(row) for row in connection.execute('''
                SELECT Interaction_ID, Interaction_Type, Author_Name,
                       Interaction_Date, Message, Shared_With_Home_Manager
                FROM HR_recognition_feedback WHERE Contribution_ID=?
                ORDER BY Interaction_Date, Interaction_ID
            ''', (item['Contribution_ID'],))]
        survey = connection.execute('''
            SELECT Survey_ID, Survey_Date, Responses, Eligible_Employees,
                   Favorable_Percent, Mean_Score, Question
            FROM HR_survey_summary
            WHERE Department=? AND Team=? AND Survey_Date=? AND Dimension='Recognition'
        ''', (manager['Primary_Department'], manager['Primary_Team'], end)).fetchone()
        comments = []
        if survey:
            for clause in ['Response_Score>=4', 'Response_Score<=3']:
                # Only fixed SQL fragments; all caller inputs remain parameters.
                comments.extend(dict(row) for row in connection.execute(f'''
                    SELECT Comment_ID, Response_Score, Response_Text
                    FROM HR_survey_comments WHERE Survey_ID=? AND {clause}
                    ORDER BY Comment_ID LIMIT 2
                ''', (survey['Survey_ID'],)))
        return dict(
            Manager=manager, Quarter=quarter, Period_Start=start, Period_End=end,
            Employees=sorted(employees.values(), key=lambda row: row['Employee_Name']),
            Counts=dict(Employees_In_Scope=len(employees), Cross_Team_Contributions=len(contributions),
                        Contributions_With_Manager_Recognition=sum(item['Has_Manager_Recognition'] for item in contributions),
                        Contributions_With_Partner_Feedback=sum(item['Has_Partner_Feedback'] for item in contributions),
                        Contributions_Without_Manager_Recognition=len(missing),
                        Partner_Feedback_Not_Shared=sum(item['Has_Partner_Feedback'] and not item['Partner_Feedback_Shared'] for item in contributions)),
            Evidence_Sample=sample, Survey=dict(survey) if survey else None,
            Anonymous_Comment_Sample=comments,
        )
    finally:
        connection.close()


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def render_report(report):
    manager = report['Manager']; counts = report['Counts']
    lines = [f'# Cross-team contribution review: {report["Quarter"]}', '',
             f'Manager: **{manager["Manager_Name"]} ({manager["Manager_ID"]})**. Team: **{manager["Primary_Team"]}**.',
             f'Contribution period: {report["Period_Start"]} through {report["Period_End"]}.', '',
             f'The manager\'s roster contains {counts["Employees_In_Scope"]} employees employed during this quarter. Their records include **{counts["Cross_Team_Contributions"]} accepted contributions to other teams**.',
             f'Of these, **{counts["Contributions_With_Manager_Recognition"]} have a manager-recognition record** and **{counts["Contributions_Without_Manager_Recognition"]} do not**. Partner feedback is recorded for {counts["Contributions_With_Partner_Feedback"]} contributions; {counts["Partner_Feedback_Not_Shared"]} have partner feedback with no recorded sharing to the home manager.', '',
             'These are documentation counts, not employee ratings or a finding of unfair treatment. The synthetic dataset caps quarterly recognition notes at one per employee and partner notes at two. Absence of a note does not establish that recognition or a conversation never happened.', '',
             '## Employee contribution records', '',
             'Employees are listed alphabetically. A zero means no matching recorded cross-team contribution in this period, not poor performance.', '',
             '| Employee | Employee ID | Contributions | With manager recognition | With partner feedback | Without manager recognition |',
             '|---|---|---:|---:|---:|---:|']
    for employee in report['Employees']:
        lines.append('| ' + ' | '.join(cell(employee[key]) for key in ['Employee_Name','Employee_ID','Contributions','Contributions_With_Manager_Recognition','Contributions_With_Partner_Feedback','Contributions_Without_Manager_Recognition']) + ' |')
    lines += ['', '## Contribution evidence to review', '',
              f'This section samples {len(report["Evidence_Sample"])} of {counts["Contributions_Without_Manager_Recognition"]} contributions without a manager-recognition record. Entries with recorded partner feedback appear first, followed by recency. This sample does not rank employees.']
    if not report['Evidence_Sample']:
        lines += ['', 'No matching contributions without manager-recognition records were found.']
    for item in report['Evidence_Sample']:
        lines += ['', f'### {item["Employee_Name"]}: {item["Project_Name"]}', '',
                  f'Accepted: {item["Contribution_Date"]}. Beneficiary: {item["Beneficiary_Team"]}.',
                  f'Evidence keys: `{item["Contribution_ID"]}`, `{item["Work_Request_ID"]}`, `{item["Employee_ID"]}`.', '',
                  item['Contribution_Summary'], '', f'Recorded outcome: {item["Business_Outcome"]}',
                  f'Evidence description: {item["Evidence_Description"]}']
        for interaction in item['Recorded_Interactions']:
            lines += ['', f'Recorded {interaction["Interaction_Type"].lower()} from {interaction["Author_Name"]}, dated {interaction["Interaction_Date"]} (`{interaction["Interaction_ID"]}`):', '',
                      interaction['Message'], f'Shared with home manager: {interaction["Shared_With_Home_Manager"]}.']
        if not item['Recorded_Interactions']:
            lines += ['', 'No partner-feedback or recognition interaction is recorded for this contribution.']
    lines += ['', '## Anonymous team survey context', '']
    survey = report['Survey']
    if survey:
        lines += [f'Team-wide Recognition question: "{survey["Question"]}"',
                  f'{survey["Responses"]} responses from {survey["Eligible_Employees"]} eligible employees; {survey["Favorable_Percent"]}% favorable, with a mean of {survey["Mean_Score"]}/5 (`{survey["Survey_ID"]}`).', '',
                  'This survey covers the whole team, including other managers\' rosters. It cannot be linked to any employee or contribution above. The illustrative comments below include favorable and lower/middle ratings and are not a representative text sample.']
        for comment in report['Anonymous_Comment_Sample']:
            lines += ['', f'- Anonymous comment `{comment["Comment_ID"]}`, rating {comment["Response_Score"]}/5: {comment["Response_Text"]}']
    else:
        lines += ['No matching team Recognition survey is available; coverage is unavailable, not zero.']
    lines += ['', '## Manager follow-up', '',
              'Review the cited deliverables and request any missing context from the receiving teams. Confirm whether recognition occurred through an unrecorded channel before deciding what acknowledgment is appropriate. Record the manager\'s follow-up and check documentation completeness in the next quarterly review.', '',
              'This report is generated from synthetic data through a fixed read-only query. It does not call an LLM. Manager selection is a demo filter, not authenticated access; production role checks and model integration remain to be implemented.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manager', required=True, help='Pilot manager ID from HR_managers.')
    parser.add_argument('--quarter', required=True, help='Calendar quarter, for example 2026-Q3.')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--database', type=Path, default=HERE / 'data' / 'echo.db')
    args = parser.parse_args()
    try:
        report = get_recognition_report(args.database, args.manager, args.quarter, args.limit)
        output = HERE / 'reports' / f'recognition_{report["Manager"]["Manager_ID"]}_{args.quarter}.md'
        output.parent.mkdir(exist_ok=True)
        output.write_text(render_report(report), encoding='utf-8')
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f'Report failed: {error}', file=sys.stderr)
        return 1
    print(f'Report saved: {output}')
    for name, value in report['Counts'].items():
        print(f'{name}: {value}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
