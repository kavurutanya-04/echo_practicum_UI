# Echo synthetic dataset: two-year reporting window

The application data covers **October 1, 2024 through September 30, 2026**, the latest 24 complete calendar months when this version was created on October 5, 2026. All supplied and generated information is synthetic. All data and documentation are in English. The application backend loads eleven `HR_` and `OP_` CSV files. Backend loading does not authorize sending entire tables to the language model.

`HR_` means Human Resources; `OP_` means operational work. `QA_` files contain audit material, generation references and private backend HR indicators. They are outside the model's general data source. The original source is retained as a historical reference; its observation dates have not been relabeled as current measurements.

## Tables and observation frequency

| File | What one row means | Frequency and coverage |
|---|---|---|
| `HR_employees.csv` | One employee with source employment dates, synthetic name, team and pilot manager | Master roster as of September 30, 2026, covering the full reporting window; hires can be older |
| `HR_managers.csv` | One manager and their synthetic team assignment | Master data covering the full reporting window |
| `HR_survey_summary.csv` | One team, quarterly survey wave and question | Eight quarterly waves, nine questions, 32 teams: 2,304 rows |
| `HR_survey_comments.csv` | One anonymous written answer with its question rating | The same eight quarterly survey waves |
| `HR_program_participation.csv` | One employee and offering; an offering is a dated learning edition or quarterly benefit-use allocation | Twelve bimonthly learning cycles and eight benefit reporting quarters |
| `HR_recognition_feedback.csv` | One documented quarterly partner-feedback or manager-recognition note about a contribution | Eight quarter-end review dates |
| `OP_projects.csv` | One team-sponsored quarterly project | Three projects per team per quarter: 768 projects |
| `OP_work_requests.csv` | One specific assignment, with requester, assignee, deliverable, hours and deadlines | Event records throughout the two-year window |
| `OP_capacity.csv` | One employee and covered working week | Weekly throughout the window; partial boundary weeks are prorated |
| `OP_priority_decisions.csv` | One decision affecting a request and its competing commitment | Event records throughout the window |
| `OP_contributions.csv` | One accepted contribution and the team benefiting from it | Event records throughout the window |

`QA_temporal_coverage.csv` shows actual record-date ranges, observation frequency, quarter coverage and row counts for each application file. A quarterly survey's first response date is the end of its first quarter, not the first day of that quarter. The dates represent the observation schedule inside the full 24-month window.

There are no additional teams, departments, program catalogs, enrollment or attendance tables. Readable names and labels are repeated where useful. IDs provide reliable joins; never join on a display name. `QA_data_dictionary.csv` defines fields, primary keys and references, including the private HR-history schema.

## Employee population and employment dates

All 2,500 source employee IDs remain in `HR_employees.csv`. Source hire dates, including dates before the reporting window, are retained. Termination dates use the documented source repairs. Employment dates overlap the reporting window for 1,950 employees: 1,901 have no recorded termination and 49 leave during the first reporting quarter. The remaining 550 are historical records with no simulated activities during the window. Continued employment for records without a termination is a synthetic scenario assumption.

No work or program activity is generated before hire or after termination. Survey eligibility is recalculated at each wave date. Weekly work starts only when the employee is employed at the request date and can remain employed through the possible completion date. People hired during a week normally enter the work simulation the following week. Capacity includes covered boundary-week working days; `Week_Start` can be September 30, 2024, while the actual `Period_Start_Date` is October 1.

Names, readable team labels and pilot manager assignments are synthetic. `Pilot_Manager_ID` aligns the employee and manager with the same team. The historical source `Manager_ID` remains in the source references; it is not the team-aligned pilot assignment. Team and manager assignments remain constant in this scenario. `As_Of_Date` and coverage dates on master records do not turn old source measurements into current observations.

## Quarterly surveys and open text

Survey and written-response dates are December 31, 2024; March 31, June 30, September 30 and December 31, 2025; and March 31, June 30 and September 30, 2026. There are no monthly survey waves.

Eight custom questions use a 1–5 agreement scale: Recognition, Role clarity, Manager support, Workload, Team climate, Development, Benefits and Engagement. Favorable ratings are 4 or 5. `Favorable_Percent = 100 * Favorable_Responses / Responses`. Eligible employees are the invitation population, not the favorable-rate denominator. These custom items are not a validated engagement index or Gallup Q12.

The ninth question is eNPS: likelihood of recommending the organization as a place to work, rated 0–10. Promoters rate 9–10, passives 7–8 and detractors 0–6. `eNPS_Score = 100 * (Promoters - Detractors) / Responses`, with range -100 to 100. Favorable fields are blank for eNPS. A recommendation rating does not replace the separate questions about managers, climate, workload or development. Definitions: [Qualtrics NPS scoring](https://www.qualtrics.com/support/survey-platform/survey-module/editing-questions/question-types-guide/specialty-questions/net-promoter-score/) and [employee engagement measurement](https://www.qualtrics.com/articles/employee-experience/measure-employee-engagement/).

Open text uses randomized combinations of dimension-specific experiences, examples, voices and reflections, with short, medium and long answers. Approximately 80% have a predominantly positive tone and 20% a predominantly negative tone across the whole dataset. Individual teams, quarters and questions need not have an exact 80/20 split. Mixed opinions include intermediate ratings; positive tone is not identical to a favorable rating. Repeated short answers are permitted because different people can give the same brief reply. These are invented template-based responses, not real collected text.

`Response_Score` is the anonymous rating submitted with the written answer. These ratings are included in the complete rating pool used to calculate the question aggregate. Remaining respondents provide ratings without written comments. The full pool includes low, medium and high ratings. The 80/20 text ratio does not mean an eNPS score of 80 or 80% engagement.

Comment rows have **no Employee_ID**. `Survey_ID`, `Team`, `Department` and `Survey_Date` identify their reporting group. `Anonymous_Response_Token` identifies one written-answer row; it cannot identify a person or link answers across questions or quarters. No token-to-person mapping exists. Therefore this version supports team response rates, not counts of surveys completed by a particular employee.

`QA_comment_generation.csv` holds intended dominant sentiment, intended length and word counts for checks and evaluation. Exclude these labels from model input. For text-only sentiment evaluation, also exclude `Response_Score` and numerical survey summaries.

## Bimonthly workshops and training

Four learning programs repeat in October and December 2024; February, April, June, August, October and December 2025; and February, April, June and August 2026. This creates twelve cycles and 48 distinct learning offerings. Workshops cover feedback and cross-team priority planning; training covers practical data literacy and role-specific skills.

`Program_ID` and `Program_Name` remain the same when a program is repeated. `Offering_ID` identifies its specific edition; `Offered_Date` is the invitation date and `Session_Date` the scheduled start, both on weekdays. Each edition has its own audience. Some editions are general; others serve exactly the two teams listed in `Target_Team_1` and `Target_Team_2`. Later editions of the same program rotate to other team pairs. Non-target teams receive no participation rows for that edition. Absence of such a row means the person was outside that offering's eligible audience, not that they declined it.

Eligible invited employees have a row even if they do not enroll. Participation status describes the recorded reporting period and distinguishes non-enrollment, enrollment without starting, partial participation and completion; an old In progress row is not a claim that the person is still taking that course today. Employees have different participation tendencies, so completed activities, hours and practical use vary between people and periods. Nobody is required to attend every edition.

## Benefits available broadly, with variable use

Flexible work hours, learning allowance, peer mentoring and wellbeing break time are available to all employed pilot staff. Benefit rows report use by quarter; quarterly accounting does not mean that benefits are available only once per quarter. A newly hired employee's offer date starts at hire when that is later than the quarter start. Benefit activity stops at termination.

Each employee can use different benefits in different quarters, or leave them unused. `Use_Count` distinguishes actual recorded use from availability or enrollment. No learning-hours measure is invented for benefit use. No medical claims, diagnoses or private personal reasons were generated.

For all programs, attendance, completion, practical application and usefulness are distinct. `Applied_At_Work` can be Yes, No or Not assessed. `Self_Reported_Use_Evidence` is an invented participant account, not proof of business impact. `Usefulness_Score` ranges from 1 to 5 and is blank when participation has not begun. Program-to-survey comparisons use team and compatible reporting periods; no individual survey linkage is possible.

## Work, contributions, decisions and quarterly feedback

Work requests explain who asked for a deliverable, who does it, why it matters, original and revised deadlines, effort and completion. Participation in project work varies by employee and week. Capacity records include routine work and leave, and unknown allocations remain blank rather than zero.

Priority decisions include moving a deadline, reducing scope, adding support, changing priority and escalating unresolved conflicts. Revised values reconcile to the request. Changing a priority label alone does not resolve a capacity conflict. Dependency delays are described separately. Quarterly project labels make repeated initiatives readable; project targets permit up to two weeks for final handoffs, capped at September 30, 2026.

Contributions retain the date work was accepted. Feedback and recognition are recorded at the end of the quarter containing that contribution. `Interaction_Date` is the formal quarterly review date, not an invented immediate conversation date. Review notes are limited to up to two partner notes and one manager-recognition note per employee per quarter. A review can discuss work performed before an employee left. Missing notes do not prove that no informal recognition occurred.

## Private quarterly HR history and source reference

`QA_hr_metrics_history.csv` provides employee-level HR indicators across all eight quarters for trusted backend calculations. Its key is Employee_ID plus Reporting_Period. It retains the source's 37-column structure and adds period, observation status, origin and training-coverage fields. A leaving employee's observation is taken at termination during their last quarter; otherwise it is at quarter end. Hire dates can be much older.

Values are a newly invented longitudinal scenario seeded from the corrected source. Salary updates, scores, absence and overtime vary under explicit generation assumptions; several demographic, role and source attributes are carried forward. These are not recovered historical observations. Tenure is recalculated at the observation date. Historical Engagement_Score and Satisfaction_Score use 0–100, unlike the new 1–5 survey items, and do not identify anonymous respondents. Do not merge them into a single scale or treat them as the same answers.

Training_Hours_Last_Year sums recorded workshop and training hours over the preceding 365 days available in this simulation. During early quarters, Training_Observation_Days and Training_Hours_Coverage_Status mark partial coverage since October 1, 2024; partial observation is not a complete prior-year total. Values are reconciled to program participation records, rather than copied from the old annual-training field.

`QA_corrected_source.csv` is the frozen, repaired 2,500-row historical source reference. `QA_original_source.csv` preserves the original byte-for-byte. Their observation dates remain historical; these two files are reference exceptions to the new reporting window. Original dates and annual measures must not be interpreted as two years of current observations. `QA_source_corrections.csv` documents each source repair: preserve hire; move impossible termination to hire plus one day; advance snapshot as necessary; recalculate tenure. Repairs are prototype assumptions, not recovered true dates.

`QA_manifest.csv` lists application and backend/reference files, row counts and purposes. `Load_Into_Prototype=No` on private or QA material means it must not be exposed as a general agent table; approved backend calculations may read the private HR history. `QA_validation.csv` records executed checks.

## Privacy and use by the agent

Keep fictional names and employee IDs where needed to demonstrate contributions and work assignments. Salary, age, gender, burnout and performance are outside the small agent-facing roster. Private source and HR-history records stay with trusted backend code. Expose named, read-only functions that check the caller's role and team, then return authorized work evidence or permitted HR and program aggregates with denominators. The agent should receive no unrestricted SQL, database-file or raw private-history access.

CSV files do not implement authentication or permissions. These are requirements for the future application. For future real surveys, review identifying details in text, present themes by team and suppress results with fewer than ten respondents under the chosen prototype reporting rule. Ten is a design choice, not a guarantee of anonymity or a legal standard.

All files use comma-separated UTF-8 with BOM, English text and ISO dates. Blank values mean unavailable or not applicable, not zero. This dataset supports two-year comparisons and hypothetical follow-up scenarios. It does not establish that benefits, training or Echo caused better engagement. No guaranteed improvement is imposed on the eight waves; label any later deliberately improved version as a simulated scenario.
