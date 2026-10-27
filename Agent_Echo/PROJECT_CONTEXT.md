# Echo: current project context

## Publication follow-up, 2026-10-27

The user subsequently authorized committing and publishing the current local code,
tests and documentation to GitHub. Earlier no-publication statements describe their
implementation stage. This follow-up changes no runtime behavior and runs no tests,
builds or model calls; review-v5 and capture/resumption remain unvalidated by execution.
Private credentials, reports, logs, checkpoints and local databases remain excluded.

## Corrected B, full capture and phase-only resumption after runs 27-29, 2026-10-27

Runs 27/28/29 all failed without completed support review: Luna 11 calls/226.735 s,
DeepSeek 25/558.000 s and Gemini 11/240.875 s. All classified 13 comments; hashes and
aggregation matched retained labels. Ten of twelve support submissions failed v4's
literal reconstruction requirement; two omitted findings. DeepSeek also failed exact
question-excerpt checks. Gemini completeness accepted actions in place of requested
questions; its candidate still overgeneralized mixed comments and proposed contacting
anonymous respondents. DeepSeek's last prose listed nine positive IDs while reporting
eight. These are format/semantic failures, not connection failures or validated accuracy.

User-approved correction now uses review-v5. Claim descriptions are concise assessments,
not literal reconstruction. Original is instructed to separate reviewable factual
assertions/premises; existing code assigns finding IDs, then IDs such as F2:A1 to review
assessments. Source subsets, explicit judgments, whole-finding withholding/repair, v3
correction judgments, both reviews, five roles and source-facts-v4 replay remain.

Full private exchanges and phase checkpoints are captured under reports/logs/details/,
with credentials omitted. Result artifacts link capture files. `--resume` accepts a new
failed artifact/checkpoint and runs that phase only; review retries never call Original
or Vanilla. Matching completed completeness can be reused; scope/source/profile/transport
changes are rejected or invalidate the affected subphase. New outputs preserve lineage
and bounded per-attempt budgets. Phase retries do not claim a complete Original answer.
Older files without checkpoints cannot automatically resume or recover missing arguments.

The user explicitly requested no local tests, builds or model calls during implementation.
Only static parsing/diff/reference review was performed; fixtures/new regressions are
unrun. Review-v4's earlier 322 checks do not validate this update. Next full runs are
30 Luna, 31 DeepSeek and 32 Gemini, to be executed by the user. See
[capture/resumption](RESUME_AND_CAPTURE.md), [commands](TESTING_AND_RAG.md#next-three-model-runs-30-32-2026-10-27)
and [history](LIVE_TEST_HISTORY.md). No GitHub publication.

## Assertion-level support review after runs twenty-five/twenty-six, 2026-10-27

Implemented user-selected option B: review-v4 assesses individual assertions inside
each finding, retaining a literal visible-text excerpt, factual/proposal kind, source
subset, explicit support judgment and reason. Ordered textual coverage and references
are checked in code; a failed assertion withholds its whole finding and creates an
Original repair despite any accepting verdict. Semantic decomposition and support remain
model judgments. V3 correction judgments, both phases, five roles, historical artifacts,
source-facts replay, provider settings and budgets remain. The technical UI shows these
assessments; manager projections are unchanged.

All 322 offline checks (including nine new regressions) and the frontend build passed.
No new provider call or GitHub publication. Live semantic improvement and suitability
for APInex's unchanged 6000-token output limit remain unverified. See the
[contract](WORKFLOW_RELIABILITY.md#assertion-level-support-review-review-v4-2026-10-27),
[validation](TESTING_AND_RAG.md#assertion-level-support-review-2026-10-27) and
[run 15-26 history](LIVE_TEST_HISTORY.md). All those saved runs predate review-v4.

Read-only inspection found run 24 partial (22 successful Luna calls, 499.937 seconds,
three drafts), run 25 failed (21 successful DeepSeek calls / 22 attempts, 460.954 seconds,
12/13 classification validated, no complete review), and run 26 complete (14 Gemini
calls, 306.156 seconds, two drafts, both final phases complete). Run 26's hashes, label
coverage, literal visible excerpts and aggregation match the database; accepted prose
nevertheless attributes inconsistent access/workload to both mixed comments when only
CMT27508 describes it. CMT27511 states frustration despite useful support. Run 24 also
calls CMT27512 positive in prose despite its stored mixed label. Acceptance is not
semantic validation. See the history for post-run changes and comparison limits.

## Additional APInex model options, 2026-10-27

Added user-requested `apinex_deepseek_test` / `free/deepseek-v4.1-flash` and
`apinex_gemini_test` / `free/gemini-3.8-flash` in connections.json. Both reuse the
APInex endpoint, APINEX_API_KEY and Luna's limits/pacing/retries. The existing Luna
profile, default and role assignments are preserved. Only configuration/offline
verification was performed; no new API call or live tool/quality validation.

## Reasoned actions and review simplification after run twenty-three, 2026-10-27

Run twenty-three was partial after four drafts, 26 successful calls and 562.578 seconds.
All drafts included the requested two questions; actions appeared in draft two but were
lost in subsequent revisions. Source/hash/coverage checks and aggregation reproduced:
13 comments, nine positive, two negative and two mixed; CMT27512 changed from mixed in
run twenty-two to positive on unchanged text. Reviews mixed false omissions/duplicate
repairs with a real unsupported attribution to CMT27511. Provider-reported usage was
323,368 tokens (294,516 input; 28,852 output), not a billing reconciliation.

The user approved at least one reasoned manager action in a complete Original analysis.
The proposal may introduce an idea outside the question and sources; its factual basis
and rationale must follow the analysis, while assumptions/possible benefits remain
proposals. Original preserves requested work and the action through repairs. Simplified
review instructions distinguish factual support, synthesis and action reasoning.
Completeness still checks the user's visible request only. Original activates a trusted
require_actionable flag for support; a missing action can be returned as policy_requirement
with Original ownership and request_excerpt=null. This avoids fabricating a user request.
The contextual kind is absent for other callers by default. Semantic presence/quality
remains model judgment; code does not infer it from punctuation or proposal-list length.
Both reviews, review-v3 lifecycle, objective gates, rubric and budgets remain. See the
[workflow](WORKFLOW_RELIABILITY.md#reasoned-actions-and-review-simplification-after-run-twenty-three-2026-10-27)
and [validation](TESTING_AND_RAG.md#reasoned-actions-and-review-simplification-after-run-twenty-three-2026-10-27).

## Requested content and additional actions after run twenty-two, 2026-10-27

Run twenty-two completed in 201.672 seconds with ten successful calls and one draft.
Read-only checks confirmed all 13 eligible source texts/hashes and label coverage,
recomputed aggregates and verified visible literal excerpts. Completeness raised three
unjustified objections; review-v3 support withdrew them without schema retries.
However, support treated the requested two team
questions as optional wording while accepting two action recommendations instead.
Classification remains provisional; CMT27512 changed from positive in runs seventeen
through nineteen to mixed in runs twenty through twenty-two on unchanged source text.

The user approved preserving useful actions as additions to the requested answer.
Original and both ZeroSugar instruction sets now distinguish requested content/item
counts from supplementary actions, using semantic judgment rather than punctuation or
fixed layouts. Actions should explain how cited findings motivate addressing a problem
or sustaining a strength; expected benefits remain proposals. No review stage, schema,
rubric, provider setting, budget or release gate changed. Run twenty-two is preserved
as pre-change evidence. See the [workflow](WORKFLOW_RELIABILITY.md#requested-content-and-additional-actions-after-run-twenty-two-2026-10-27)
and [validation record](TESTING_AND_RAG.md#requested-content-and-additional-actions-after-run-twenty-two-2026-10-27).

## Explicit correction judgments after run twenty-one, 2026-10-27

Run twenty-one was partial after 26 successful calls and four drafts. No duplicate review
calls occurred; all completeness phases completed on their first attempt. Two support
phases failed on correction coverage/replacement references; two completed. Obligations
grew 3/6/9/12, and the final review kept optional or contradicted objections pending.
The source table remained 13 comments: 8 positive, 2 negative and 3 mixed. This established
the need for the user-approved correction-contract update, not a new agent.

Implemented review-v3: code supplies every correction_judgments key; the model returns
mandatory/addressed booleans plus a reason. Code derives canonical states and routing;
models no longer manage replacement IDs or consolidation graphs on this path. Real
required/unaddressed omissions remain pending, while explicit not-required judgments
withdraw unjustified objections. Current objections judged already visibly addressed
are withdrawn; inherited ones are resolved. No prose/keyword rule infers these judgments.
Full repair text is sent once in review_obligations; previous_corrections contains IDs
only, and the completeness summary omits its repeated correction/issue lists. All
obligations and source evidence remain present. Legacy v2 submissions retain their
validators and conservative guard and are labeled v2; saved artifacts are not rewritten.

147 focused checks across review contracts, recovery, diagnostics, workflow and adapters
passed. After retained failed prototype checks, a support-only recheck reused run
twenty-one's completed completeness review for the identical candidate/source identity.
It assessed all 16 obligations using mandatory/addressed in one live call without
rejections: six withdrawals, ten retained inherited obligations and one new correction
(eleven active repairs), no deterministic issues, and a revise verdict. Output was 3515
tokens within the unchanged 6000 limit. The model still invented a denominator-sentence
requirement and retained redundant work; this confirms contract execution, not semantic
quality or full workflow improvement. Evidence:
reports/review_v3_check_21_20261027_support_only.json and
20261027_144043_c31c613c57d1.jsonl. Live checks and their limits are recorded in
[the testing guide](TESTING_AND_RAG.md#explicit-correction-judgments-after-run-twenty-one-2026-10-27).
Both reviews, all five roles, source-facts replay, source/privacy/arithmetic gates,
sentiment guidance/context, provider configuration and budgets remain. The UI still
consumes canonical review fields and exposes no new manager workflow. No full Original
rerun, broad suite, UI build, commit or GitHub push.

## Run twenty and single-call transport, 2026-10-27

Run twenty failed after 11 successful calls: completeness rejected its first rationale
and then received two submit_completeness_review calls on each of two retries. No
support review completed. The original diagnostic did not retain rationale type/length,
so its exact failed condition cannot be recovered. Runs seventeen through nineteen
had no duplicate completeness calls. The missing single-call transport setting already
existed; these observations do not establish that forwarding strict caused duplication.

ChatModel now sends parallel_tool_calls=false when exactly one tool is offered and
required. Other tool modes retain their previous behavior; multiple-call responses are
still rejected by the review gates. Invalid completeness rationales now report type,
character count (strings only) and the 1200-character bound without retaining content.
Thirty-six focused provider/field-diagnostic checks passed. A live recheck of only the
saved run-twenty completeness phase completed on the first call, with both strict=true
and parallel_tool_calls=false captured at the SDK boundary and one returned tool call.
Its valid verdict was revise, score 2; this is phase/transport evidence, not approval of
the complete answer or validation of the semantic objections. Local metadata:
reports/completeness_transport_check_20_20261027.json; log
20261027_063645_1ecd888e5f0a.jsonl. The original run remains unchanged.

No full workflow rerun, broader suite, commit or GitHub push. Correction-protocol
alternative B remains deferred; both reviews, source/privacy gates and budgets remain.

## Strict Chat transport follow-up, 2026-10-27

Run nineteen remained partial after four drafts; contextual numeric fields were omitted
correctly, but support submissions still failed and correction obligations grew from
five to eleven. Two independent review phases already existed. Do not describe missing
phase separation as the cause or treat schema conformity as semantic correctness.

Implemented alternative A: ChatModel now preserves an explicitly supplied strict value
when converting tools to Chat Completions, including false, without adding an absent
flag or mutating the original tools. Thirteen object-schema declarations were checked
for closed properties and complete required fields; no schema changes were needed.
Three focused adapter checks passed. APInex free/gpt-6-luna accepted two live strict
requests without employee data: the existing connection probe and a synthetic packet
using ZeroSugar's nested support schema. The latter matched its fixture and schema.
Local evidence: reports/strict_transport_probe_20261027.json and logs
20261027_061516_7cc233292e46.jsonl / 20261027_061641_f1a8f52f745b.jsonl.
An initial sandbox connection attempt failed before the successful network-enabled probe.

This verifies transport and observed schema conformity, not constrained-decoding
enforcement, semantic quality or improvement on the complete Recognition workflow.
Other Chat providers were not called. Alternative B (simplifying correction judgments
and state administration) remains deferred; both review phases, current correction
retention/withdrawal rules, source/privacy gates, prompts and budgets are unchanged.
No full-suite run, complete analytic rerun, commit or GitHub push. See
[strict transport checks](TESTING_AND_RAG.md#strict-chat-transport-follow-up-2026-10-27).

## Run eighteen and contextual review fields, 2026-10-26

Observed `apinex_prueba_vanilla_18.json` / `20261027_004732_89cb24d6210d.jsonl`
(UTC log name; local date October 26): complete, 27 successful calls, 530.453 seconds,
four drafts. ZeroSugar used 15 calls; nine support submissions failed across the first
three candidates. Final acceptance required both phases on draft four. V3 rubric/full
13-comment context were active; read-only source/label/aggregate checks matched run
seventeen. Final prose gave limited pattern synthesis. This is recovery evidence, not
a demonstrated quality improvement.

Implemented the user-approved follow-up locally: per-candidate support schema omits
numeric_reviews and correction_reviews when their trusted task lists are empty. Echo
fills only these inactive lists with []; any supplied inactive entries are ignored with
metadata-only diagnostics. Active obligations/numeric requests still require complete
valid assessments. Feedback uses the actual contextual schema, rebuilt per candidate;
all semantic judgments, gates, roles, v3 rubric, full source context and budgets remain.
Existing diagnostic fixtures and focused contextual-field checks were aligned without
execution. No tests, API calls, commit or GitHub push. See the
[contract](WORKFLOW_RELIABILITY.md#contextual-support-review-fields-after-run-eighteen-2026-10-26).

## General semantic guidance after run seventeen, 2026-10-26

Run seventeen (`apinex_prueba_vanilla_17.json`, log `20261026_231553_53fb1a92e8d9.jsonl`)
completed with nine successful calls, 171.109 seconds, one candidate and both reviews
accepted. Support received all 13 full response/label pairs using rubric v2. Read-only
source checks confirmed coverage, hashes, literal structured excerpts and arithmetic.
The user considers CMT27512's positive interpretation defensible and rejected further
case-specific label rules. Citation attribution and three questions instead of two remain
observed output limitations; this run is not a classifier-quality benchmark.

Implemented the approved simplification locally: new shared rubric v3 gives general
category definitions and leaves contextual interpretation to the model. Removed
case-specific live classification/review instructions. Stored v1/v2 definitions remain
for historical review; no artifacts were rewritten. Full comment context, correction
request grounding, both reviews, four drafts, diagnostics and all data/privacy/budget
controls remain. Existing review fixtures and sentiment-version/source assertions were
aligned without execution. No tests, model calls, commit or GitHub push. Current live
quality remains unverified. See the [current guidance](WORKFLOW_RELIABILITY.md#general-semantic-guidance-after-run-seventeen-2026-10-26).

## Run sixteen and local semantic-review update, 2026-10-26

Observed `apinex_prueba_vanilla_16.json` / `20261026_205443_d0fc0454b26f.jsonl`:
complete after 15 successful calls (Original/Vanilla/ZeroSugar: five each), 291.531 seconds
and two candidates, with both final review phases accepted. Read-only replay confirmed
all 13 authorized anonymous Recognition comments for M14's Data Platforms team, unchanged
hashes, literal excerpts and 9 positive / 2 negative / 2 mixed counts. No neutral or
indeterminate labels. CMT27512 changed mixed to positive versus run fifteen on unchanged
text. Review demanded unrequested neutral examples and formatting, then introduced and
accepted incorrect coverage-to-indeterminate reasoning and mixed/neutral boundary wording.
This is operational recovery evidence, not validated classification or review quality.

Implemented locally at the user's request, without tests, API calls, commit or GitHub push:
shared `survey-sentiment-v2` definitions for Vanilla and ZeroSugar, stored rubric identity
and v1 replay for older reports; request-grounded omission corrections with retained
literal question excerpts; stronger reassessment/challenge instructions using the existing
obligation lifecycle. All canonical comments from privacy-released groups now accompany
the summary; support receives full response/label/reason pairs and their versioned rubric.
Suppressed texts remain excluded; coverage diagnostics contain counts/versions only.
Oversize complete review input fails at the existing bound rather than substituting a
sample. Five roles, provider settings, budgets, source gates and source-facts-v4/v1-v3
remain. No automatic semantic relabeling or wording-pattern rejection was added.
Tests and live behavior for this update remain unverified; preserve run sixteen and use
a fresh artifact for any later authorized evaluation. See the
[workflow](WORKFLOW_RELIABILITY.md#sentiment-and-correction-grounding-after-run-sixteen-2026-10-26)
and [validation status](TESTING_AND_RAG.md#semantic-review-update-after-run-sixteen-2026-10-26).

## Run fifteen and local review recovery, 2026-10-26

The first run fifteen failed with HTTP 504 during planning (one attempted call, no
successful calls), log `20261026_185354_9256ff04815d.jsonl`. Its JSON was overwritten
by the user's repeat under the same filename; the original log remains. The repeat,
`20261026_185739_726c29abd0f2.jsonl`, failed after 13 successful calls / 248.766 seconds,
with 19 calls and about 754 seconds left. New diagnostics worked: completeness repaired
object-valued suggestions on turn three; support then omitted clarification_question,
omitted suggestions, and attempted resolved on a current completeness correction.
The last old rejection did not identify which correction. No complete support review
or Original revision occurred. Source replay confirmed 13 eligible anonymous comments
in M14's only authorized team, Data Platforms, unchanged source hashes, literal stored
excerpts and aggregate counts: 8 positive, 2 negative, 3 mixed, zero neutral/indeterminate.
CMT27512 changed positive to mixed versus run fourteen on unchanged text; semantic label
accuracy remains unvalidated. The draft omitted requested visible literal excerpts and
said 'Both mixed comments' despite three mixed labels. Completeness falsely claimed
three categories were absent even though all five appeared in the table.

Implemented locally at the user's request, without GitHub publication: optional review
annotations normalize neutrally with diagnostics; invalid closure of a current correction
keeps it pending without discarding the support review. False omissions may be withdrawn
against visible content. Exhausted invalid support can return validated repair instructions
to Original within the four-draft bound, without a completed review or any release;
both phases must succeed on the revised answer. Completeness now sees trusted scope/team
context, without source evidence. Original/Vanilla instructions distinguish examples from
category totals and requested visible quotes. The user subsequently approved four total
drafts (initial plus three revisions) and recovery after any of the first three drafts.
ZeroSugar retains three attempts per phase; success stops early and shared budgets still
take precedence. No provider/model/shared-budget/rubric changes.
See [workflow](WORKFLOW_RELIABILITY.md#review-recovery-after-run-fifteen-2026-10-26) and
[offline validation](TESTING_AND_RAG.md#review-recovery-checks-2026-10-26). Live behavior
after this update, classifier accuracy and provider strict support remain unverified.

## Run fourteen and field diagnostics, 2026-10-26

Observed `apinex_prueba_vanilla_14.json` / `20261026_101230_bbbaadd0c825.jsonl`:
failed after 12 successful calls / 233.438 seconds, with 20 model calls and about 770
seconds remaining. Planning correctly selected Vanilla only. All 13 source texts,
hashes, labels (9 positive, 2 negative, 2 mixed), literal excerpts and aggregates matched;
the first candidate included the requested examples and used v4 without automatic
synthetic-data wording. Completeness repaired an object-valued suggestion, then returned
five issues including unjustified scope/source/method/layout objections. All three
support submissions failed top-level field validation. Their exact missing/extra fields
were not captured and cannot be recovered from this log. No completed support review or
Original revision occurred; the original artifact is retained unchanged and ignored.

Implemented the authorized diagnostic-only follow-up: schema-derived field comparisons,
bounded/redacted missing/additional-field capture in artifacts/logs/model feedback, and
phase/candidate/schema/condition identity across retries. Repeated versus changed errors
are distinguished; valid submission repairs emit a linked event. No semantic review rule,
provider setting, source contract, role or execution budget changes in this follow-up.
Completion-scope/source-legitimacy behavior and provider strict-mode compatibility remain
separate pending work. See [workflow details](WORKFLOW_RELIABILITY.md#field-error-diagnostics-follow-up-2026-10-26)
and [validation](TESTING_AND_RAG.md). The 279-test offline suite passed, including
nine new diagnostic regressions, on Windows Python 3.12.10. No new live-provider
request was made.

## Review/data update after runs twelve and thirteen, 2026-10-26

Implemented the user-selected general update: data-origin-neutral analysis across all
five roles and new outputs; Original retains analysis coordination and manager action
proposals without a checklist or another agent. `review-v2` uses one correction list,
complete obligation assessments, explicit withdrawal/consolidation, and model review
of pending metric relevance. Existing objective gates and two review stages remain.
`source-facts-v4` removes automatic origin claims; v1/v2/v3 replay is preserved. Partial
release retains the reviewed version separately from a newer unreviewed draft. UI text,
status/count projection and new chart exports are aligned. Configuration, source data,
budgets, classification rubric and the five roles are unchanged.
See the [current workflow](WORKFLOW_RELIABILITY.md#review-and-data-contract-update-2026-10-26)
and [validation record](TESTING_AND_RAG.md). All 270 offline tests passed on Windows
Python 3.12.10, the frontend production build succeeded, and runs twelve/thirteen
replayed exactly. Run fourteen above exercises this version; a complete successful
live result remains unverified.

Observed run twelve: `apinex_prueba_vanilla_12.json`, log
`20261026_091358_6b0386f57c31.jsonl`: failed after 12 successful calls / 231.75s;
13 labels (9 positive, 2 negative, 2 mixed), sources/excerpts/aggregation reproduced.
Visible excerpts were absent. Completeness requested revision; support had three
invalid submissions. An unrequested pending survey trend could also force Cherry work.

Observed run thirteen: `apinex_prueba_vanilla_13.json`, log
`20261026_092301_3a80945b0f39.jsonl`: partial after 14 successful calls / 265.375s;
identical source hashes and labels. The first review supported seven blocks and requested
repairs. Original added literal positive/critical/mixed excerpts in its second draft;
that draft's completeness review failed three structural attempts. Published blocks
came from the first reviewed draft. Review feedback also contained duplicate repairs,
unjustified data-origin objections and inconsistent routing. Classification semantics
remain unvalidated. Both original artifacts are preserved and not committed.

Reviewed: 2026-10-26 (America/New_York). This is a short entry point for future chats. It describes the local files inspected on this date; verify relevant sources before changing behavior. It is not a benchmark report or a transcript of every project conversation.

## Audit follow-up, 2026-10-26

The user authorized the three core-only updates, quick offline tests and GitHub publication.
ZeroSugar now requires assessments of every prior correction even if the response omits
`correction_reviews`; legacy reviews without pending corrections remain readable.
Responses requests and usage logs honor the profile's `max_output_tokens`, retaining the
3500 fallback. Budgeted generation calls share their existing deadline with Chat's
explicit attempts, which recheck it after pacing and before sending. Waiting/in-flight
requests are not cancelled; SDK-internal retries retain their existing settings.
The five roles, source-facts-v3/v1/v2 contracts, provider configuration and Echo_UI are
unchanged. See the [workflow follow-up](WORKFLOW_RELIABILITY.md#audit-follow-up-review-coverage-output-limits-and-request-deadlines-2026-10-26)
and [focused validation](TESTING_AND_RAG.md). The 121 focused offline checks passed on
Windows Python 3.12.14, including eight new regressions. Two older revision fixtures were
updated to assess their pending corrections. No full-suite or live-provider run was made.

## Purpose and architecture

Echo is the Practicum HR/people-analytics prototype. It uses synthetic employee data to support manager review. The application runs in a terminal and exports local artifacts; a local web UI is also available in [Echo_UI](../Echo_UI/README.md).

Local UI setup, 2026-10-22: copied only `Echo_UI/` from `origin/main` at `fcc014a`, preserving the existing uncommitted agent changes. Built the frontend and started FastAPI at `http://127.0.0.1:8765` using the separate Windows Python 3.12 environment `Echo_UI/.venv-windows`. HTTP checks confirmed the page, M14 lookup and scoped overview; browser inspection confirmed M14's manager workspace in its default Demo mode. No analysis or live model call was run. This verifies local UI startup, not answer quality. The repository's `start.sh` is for macOS/Linux; this local Windows server was started directly with `.venv-windows/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8765` from `Echo_UI/backend/`. The existing local Git branch was not merged or committed.

| Role | Current responsibility | Main implementation |
| --- | --- | --- |
| Original | Plan the analysis, select specialists, integrate proposed actions, and coordinate corrections. | [original.py](agents/original.py) |
| Cherry | Obtain scoped numeric evidence through SQL and prepared metrics. | [cherry.py](agents/cherry.py), [metrics.py](agents/metrics.py) |
| Vanilla | Retrieve source-linked text and classify scoped survey sentiment when requested. | [vanilla.py](agents/vanilla.py), [tools.py](agents/tools.py), [semantic_search.py](agents/semantic_search.py) |
| Lime | Select supported charts from Cherry's evidence and export accepted SVG/CSV/provenance artifacts. | [lime.py](agents/lime.py), [chart_export.py](agents/chart_export.py) |
| ZeroSugar | Review evidence, findings, and chart plans; identify corrections. | [zero_sugar.py](agents/zero_sugar.py), [findings.py](agents/findings.py) |

Typical flow: question/scope -> Original's plan -> Cherry and/or Vanilla -> candidate answer -> Lime when needed -> ZeroSugar -> accepted output or localized correction. Specialists are selected by need, not always all invoked. Final states include `complete`, `partial`, `needs_clarification`, and `failed`.

Specialists can also return structured `declined` or `incomplete` task outcomes. Original
uses those to correct routing or explain unresolved work; a decline does not prove absent
data. Sentiment-label counts belong to Vanilla; SQL/rating metrics belong to Cherry.

Unsupported findings are withheld. Independently supported blocks may be released as partial output; charts are withheld for incomplete packages. A missing recognition record is not proof that recognition never occurred. Sentiment prevalence requires the complete eligible population, not selected search hits.

Sources: [AGENT_ROLES.md](AGENT_ROLES.md), [WORKFLOW_RELIABILITY.md](WORKFLOW_RELIABILITY.md).
The [documentation map](DOCUMENTATION_MAP.md) lists every current guide, coding-assistant
instruction file and local historical reference. `AGENTS.md` guides project maintenance;
`agents/policies.py` supplies the shared rules actually composed into model calls.

## Retrieval and configuration

- Default text retrieval is local SQLite FTS5/BM25. Semantic and hybrid retrieval are optional and use a separately configured embedding provider. A graph is not required by the existing RAG.
- [connections.json](connections.json) is the current source for non-secret models, endpoints, API versions, limits, default profile, and role assignments. Current [connections.py](agents/connections.py) rejects the old model/endpoint environment-reference fields. Prefer this code and [TESTING_AND_RAG.md](TESTING_AND_RAG.md) over older setup paragraphs when they conflict.
- Credentials alone are loaded from the ignored private `.env` or process environment. Do not inspect them for orientation.
- The configured shared default is `gw_azure`; role assignments are currently unset and inherit it. `google_test` currently names `gemini-3.5-flash-lite`. Other provider profiles are experiments, not automatic fallbacks or proof of availability. An explicit `--profile` selects the profile for that run.
- No OpenRouter profile exists in the inspected configuration. Paid comparisons and Graphify were discussed in chat; this task does not implement either integration or select a winning model.
- Added on 2026-10-20: optional `apinex_test` uses the existing Chat Completions adapter with `https://api.apinex.bond/v1`, `free/gpt-6-luna`, and the private `APINEX_API_KEY`. The user selected Luna for all roles via `--profile apinex_test` and 20-second request spacing (3 RPM target). [request_pacing.py](agents/request_pacing.py) shares spacing and HTTP 429 cooldowns by endpoint/credential within one process; two bounded retries honor `Retry-After` with fallback backoff. SDK retries stay disabled. Existing model-turn and elapsed-time budgets remain unchanged; waits consume elapsed time. Separate processes are not coordinated. The user approved raising the shared Luna output allowance from 3500 to 6000 tokens. The connection probe confirmed one real tool call on this date; this is not proof of analytic quality. See [APInex setup and probe](TESTING_AND_RAG.md#apinex-sdk-trial).

## Current implemented contracts

Selected autonomy/review update, 2026-10-23: implemented 1A/2A/3A/4A/5B/6A/7B/8A.
Original's role instructions are consolidated and favor integration of adequate specialist
analysis without losing meaning. The mandatory deliverable checklist is retired; only
actual review corrections persist. ZeroSugar now performs separate visible-answer
completeness and evidence-support calls. The first call sees question/answer and visible
chart labels when present, without source data; its
omissions cannot be overridden by later source acceptance. Code attaches citations to
reviewed finding IDs. New phase diagnostics contain counts/status metadata only. Existing
five roles, specialist formats, sentiment repair, routing flags, scope/privacy gates and
source-facts-v3/v1/v2 replay remain. No provider/model configuration is changed. The agent
suite passed 242 offline tests on Windows Python 3.12.14, including 19 new regressions;
initial baseline was 223 tests with 15 failures and 4 errors. Earlier tests were aligned
with explicit v2 replay/current v3 contracts, and partial-result compatibility was repaired.
No live provider call was performed. The user authorized GitHub publication after tests.
One additional normal review call per candidate consumes the existing budgets; live quality,
cost and latency are still unmeasured. See the [current workflow](WORKFLOW_RELIABILITY.md#autonomous-synthesis-and-two-stage-review-2026-10-23).


Historical first-stage coordination update, 2026-10-22, after run ten (checklist retired on 2026-10-23): Original's existing plan now
requests literal request-derived deliverables with analytical owners. The checklist
accompanies specialist assignment, final synthesis and review; the original question
remains authoritative. Existing Vanilla/Cherry answer/evidence formats and standalone
commands remain. ZeroSugar returns explicit corrections per mandatory issue, including
owner, requested change and available sources, and assesses each previous pending item
on the next candidate while reviewing the entire revised package. Optional wording is
a suggestion, not a reason to block. Partial output names current reviewed gaps rather
than inferring them from the agent targeted for repair. Older planning/review fields
remain readable; no source-facts-v3 answer or v1/v2 replay change is introduced. Code
checks structure/references, not semantic completion. No tests, replay, provider calls,
commit or GitHub publication were performed at that initial stage, as requested. The existing
revision/call/time/token limits remain. Evidence-only handoff is still deferred. See
[coordination contract](WORKFLOW_RELIABILITY.md#requested-deliverables-and-explicit-corrections-2026-10-22).

Publication follow-up, 2026-10-22: the user subsequently authorized committing and pushing
the pending coordination code and reference updates, incorporating the group's UI commits
from `origin/main`. This publication does not validate runtime behavior or answer quality;
no new runtime tests, artifact replay or provider calls are part of this follow-up.

First-stage v3 update, 2026-10-21, after run nine: narrative quantities/quantifiers now
produce nonblocking review warnings, not automatic answer rejection. Interpretations may
cite text or source rows with `quote=null`, regardless of source count; supplied illustrative
quotes remain literal. Whitespace and unambiguous known citations normalize without a
repair turn. ZeroSugar receives flagged claims and available computed comparisons, and
explains their support/uncertainty in per-finding reasons. Code still verifies scope,
sources, exact excerpts, coverage and controlled calculations; it does not assign sentiment
or prove prose meaning. Rejections/normalizations retain bounded redacted narrative context
and feedback; warning assessments are logged. Saved v1/v2 rendering remains implemented.
No tests, artifact replay or API calls were run, by user instruction; only static review.
At that point the proposed next filename was `apinex_prueba_vanilla_10.json`; its later
observed result and the current next filename are recorded below.
A successful answer remains the goal, not a demonstrated outcome of these code changes.
Specialist evidence-only handoff remains a separate second-stage proposal. See
[v3 workflow](WORKFLOW_RELIABILITY.md#narrative-review-signals-and-presentation-v3-2026-10-21)
and [source contract](SOURCE_GROUNDING.md).

Planning update, 2026-10-21, after run eight: Original normalizes an unused clarification
basis to null when no clarification question is proposed, preserving all other plan checks
and the two-attempt limit. Rejected/normalized attempts retain bounded, redacted received
clarification values, cause and feedback in JSONL and `diagnostics.planning_attempts`,
including on failure. Real clarification requests still require a valid basis and
reconsideration. Redaction covers recognizable patterns, not every possible personal
detail; artifacts remain local. No tests or API calls were run, as requested. Prior test
results predate this change; live confirmation is pending. See
[planning normalization](WORKFLOW_RELIABILITY.md#planning-normalization-and-diagnostics-2026-10-21).

Historical synthesis/presentation update, 2026-10-21: v2 allowed several cited
text sources to support a provisional synthesis with `quote=null`, while individual
examples still need literal excerpts. Exact source tables suppress repeated cell sentences,
and narrative labels are grouped. Original preserves facts/meaning/provenance during
repair without freezing the previous layout. ZeroSugar checks all cited sources and
separates mandatory `issues` from optional `suggestions`. Stored v1 answers retain their
original replay contract. Five roles, existing tools, scope/privacy gates and 6000 APInex
output tokens were unchanged. Only focused final offline checks were authorized; no initial,
general or live test was part of that update. See
[the contract](SOURCE_GROUNDING.md) and [workflow](WORKFLOW_RELIABILITY.md#cited-synthesis-and-presentation-2026-10-21).
Final evidence: 36 focused offline tests passed. The saved seventh-run v1 candidate still
passes source-claim replay; its same selection renders as 10 blocks in v2 instead of 21,
without the repeated cell sentences. No saved artifact was overwritten or live model run
performed. These checks do not certify future agent compliance or sentiment semantics.

The approved updates on 2026-10-20/21 preserve the five roles, source restrictions and
independent review. Detailed change history belongs in the linked operating guides;
the observed live runs are recorded separately below.

| Area | Current behavior | Detailed reference |
| --- | --- | --- |
| Numeric evidence | Original plans all needed dimensions; Cherry retains metric/schema/SQL tools and reuses completed work. Models select source facts; Python renders tables, differences and matched-date comparisons. | [Source contract](SOURCE_GROUNDING.md), [workflow](WORKFLOW_RELIABILITY.md) |
| Shared instructions and scope | Six rules in `agents/policies.py` reach every analysis call path. A proposed initial clarification must identify a missing detail and reconsider the full request within the existing two planning attempts. Normal planning adds no call. | [Shared rules](WORKFLOW_RELIABILITY.md#shared-rules-and-initial-planning-clarifications-2026-10-21) |
| Text classification | Original distinguishes full sentiment from SQL ratings. Vanilla uses batches of 20, three attempts per batch, retained valid records/counters within the same workflow, literal quotes up to 400 characters and separate explanations up to 160. No partial percentages. | [Role contract](AGENT_ROLES.md), [sentiment repairs](WORKFLOW_RELIABILITY.md#sentiment-routing-retained-progress-and-task-declines-2026-10-21) |
| Individual text sources | Publishable summary examples also become canonical `survey_response` evidence for Vanilla/Original citations; ZeroSugar checks the actual scoped response, labels, hashes, coverage and aggregation. Labels/interpretations remain provisional. | [Source grounding](SOURCE_GROUNDING.md) |
| Task outcomes | Cherry, Vanilla and Lime can decline incompatible work in an existing turn. Original can correct routing and reuses identical closed-task outcomes. Missing evidence, incomplete work and failure stay distinct. No new agent or mandatory preflight call. | [Workflow repairs](WORKFLOW_RELIABILITY.md#sentiment-routing-retained-progress-and-task-declines-2026-10-21) |
| Diagnostics and release | V3 answer rejections/normalizations retain bounded redacted narrative context and feedback; batch diagnostics stay minimized. Narrative warnings reach ZeroSugar without becoming integrity errors. Unsupported findings stay withheld; complete status requires completed review and requested coverage. | [V3 diagnostics](WORKFLOW_RELIABILITY.md#narrative-review-signals-and-presentation-v3-2026-10-21), [CLI guide](README.md) |

The earlier full implementation check passed **207 offline tests on 2026-10-21**, including
22 [sentiment workflow regressions](tests/test_sentiment_workflow_repairs.py), without
provider requests. Scripted labels test contracts, not model quality. The current
documentation review did not rerun that suite. Live confirmation of the fifth-run repairs
and independently measured sentiment quality remain pending.

Later repair, 2026-10-21: permit quarter/ISO-date references, provide precise structured
citation feedback and repeated-error guidance, reuse retained specialist evidence for
independent review, and distinguish failed/unexecuted reviews. Lime and ZeroSugar retain
minimized repair diagnostics; provider token counters and failure stages improve local
diagnosis. Roles, tools, APInex's 6000 tokens and all execution budgets are unchanged.
The 75 focused offline checks listed in TESTING_AND_RAG.md passed; the full suite was
not rerun and live confirmation remains pending. See
[repair and recovery](WORKFLOW_RELIABILITY.md#repair-feedback-and-retained-evidence-2026-10-21).

## What is implemented versus demonstrated

Engineering checks/demo use scripted or mocked model responses. A connection probe establishes API/tool access for that request. A live answer establishes an observed execution, not general analytical accuracy. Model acceptance is not independent human validation.

Live testing has already begun. The following existing local artifacts were inspected for mode, status, call counts, and verification metadata through 2026-10-21:

| Artifact under local `reports/` | Observed metadata |
| --- | --- |
| `prueba_gemini_encuestas.json` | `live`, 7 successful Gemini calls, `complete`, verifier `accept`. |
| `workflow_improvements_live_check_v4.json` | `live`, 8 successful NVIDIA calls, `partial`, verifier `revise`. |
| `apinex_prueba_media.json` | `live`, 17 successful Luna calls, `failed`; Vanilla quote validation failed and all three ZeroSugar review attempts were invalid. The earlier log does not identify the exact invalid review field. |
| `apinex_prueba_media_corregida.json` | Follow-up attempt could not connect, zero successful API calls, `failed` with `provider_connection`. It does not test the corrected model behavior or 6000-token support. |
| `apinex_prueba_media_actualizada.json` | User's live follow-up: 19 successful Luna calls, `partial`, 5 released findings; both dimensions retrieved. Original delegated sentiment to Cherry, the table lacked in-block citations, and ZeroSugar approved contradictory comparison prose. Vanilla was not invoked. This demonstrated a grounding/semantic-review gap, not successful analytic validation. |
| `apinex_prueba_media_3.json` | User's third live run: 1 successful Luna planning call, `needs_clarification`. Original incorrectly asked to complete an already complete question. No data tools, specialists or source-bound final answers were exercised. The shared-policy/clarification update followed this observation. |
| `apinex_prueba_media_4.json` | User's fourth live run: `complete`, 9 successful Luna calls, verifier `accept`, 14 reviewed units, 168.718 seconds. Original 4 calls, Cherry 4, ZeroSugar 1; Vanilla/Lime skipped. Source aggregates and numerical changes independently matched. Four source submissions were corrected; their exact rejected arguments were not preserved and cannot be recovered. The gateway file reports 71,630 actual tokens and 214,890 quota units (x3). Final prose is repetitive, changing response denominators deserve fuller explanation, and one ZeroSugar rationale has a reversed comparison sign despite the correct coverage count. This is an observed numeric success, not general model/text quality validation. |
| `apinex_prueba_vanilla_5.json` | User's fifth live run: `failed`, 28 successful Luna calls, 545.36 seconds; Original 8 calls, Vanilla 13, Cherry 7, ZeroSugar 0. Incorrect routing, repeated classification and missing individual text sources exhausted the workflow. The third Vanilla delegation retained 13 complete labels (8 positive, 3 negative, 2 mixed), but no independent review occurred and no answer was released. Gateway usage: 151,229 actual tokens / 453,687 quota units (x3); no HTTP 429 observed. The repairs above follow this failure and have not yet been tested live. |

Sixth-run observation, 2026-10-21: `apinex_prueba_vanilla_6.json` and
`logs/20261021_140043_cc88dedfe33b.jsonl` record 14 generation attempts, 13 successful calls,
270.188 seconds and final `failed`. Thirteen provisional labels were retained (9 positive,
2 negative, 2 mixed). Vanilla's later generation hit the output limit; Original exhausted
seven turns after six validation rejections, including two `Q3` matches. ZeroSugar made
zero calls; `revise` was the failure default, not an independent verdict. Semantic label
quality and live confirmation of the new repair remain pending.

These files are ignored local artifacts and may be absent in another checkout. Their metadata was checked; this maintenance task did not rerun them or certify the findings. Do not describe all live evaluation as unstarted. A comparative winner remains unestablished.

Seventh-run observation: `apinex_prueba_vanilla_7.json` and
`logs/20261021_151118_6e9a78baa4d6.jsonl` record `partial`, 18 successful calls and 349.719
seconds (Original 7, Vanilla 6, ZeroSugar 5). The 13 labels cover unchanged sources:
8 positive, 2 negative and 3 mixed. CMT27512 changed from positive to mixed. Quotes,
hashes and aggregation matched the scoped source in a read-only audit; semantic accuracy
remains unvalidated. Both reviews supported all 21 blocks with no deterministic issues,
but requested synthesis/presentation repair. The old format repeated 11 numeric cells
after the table. Current changes follow this observation; no live confirmation is claimed.

Eighth-run observation: `apinex_prueba_vanilla_8.json` and
`logs/20261021_171341_9c0e36b4cea2.jsonl` record `failed`, two successful calls and
25.187 seconds. Original's plans were rejected for `unexpected_clarification_basis` then
`clarification_basis_required`. No specialist, data tool or independent review ran. The
planning update above follows this failure; the saved run is preserved unchanged.

Eleventh-run observation, 2026-10-22: `apinex_prueba_vanilla_11.json` and
`logs/20261022_185013_34573b500c0b.jsonl` record `complete`, 9 successful calls
(Original 3, Vanilla 4, ZeroSugar 2), 172.812 seconds and one candidate. Source coverage,
hashes, excerpts and aggregation matched 13 comments (8 positive, 2 negative, 3 mixed)
in the read-only audit. Vanilla repaired one nonliteral excerpt; ZeroSugar repaired an
F2 citation submission, then accepted all eight blocks. Requested literal examples were
still absent from both visible answers, despite being present in attached evidence. The
verifier's completeness rationale incorrectly treated them as displayed. No Original
correction pass ran. Synthesis also blurred favorable recognition with access concerns.
The deliverable list was not persisted by the diagnostic allowlist, so its contents cannot
be reconstructed. This exposed review/trace limitations, not validated classifier quality.
The selected 2026-10-23 update follows this result. Preserve run eleven; a later authorized
live attempt should use a fresh filename such as `apinex_prueba_vanilla_12.json`.

Tenth-run observation, inspected 2026-10-21/22: `apinex_prueba_vanilla_10.json` and
`logs/20261021_233751_93460f0e607c.jsonl` record `partial`, 12 successful Luna calls
(Original 4, Vanilla 4, ZeroSugar 4) and 228.875 seconds. All 13 comments were classified
(8 positive, 2 negative, 3 mixed; zero neutral/indeterminate); current scoped source IDs,
hashes, literal excerpts and aggregation matched in a read-only audit. They belong to
SUR2134, dated 2026-09-30. Vanilla's batch repaired two nonliteral excerpts; each review
repaired a rating-schema submission. The final review supported all six included blocks
with zero deterministic issues but requested the positive/critical literal examples
missing from the visible answer. Both examples were already in attached evidence.
Original added patterns during its one correction pass but still omitted the examples;
two candidate versions exhausted the revision bound, not the 1000-second allowance.
The reviewer also objected to usable "ask the team:" question phrasing. Semantic labels
remain provisional; this result does not validate the new coordination update. Preserve
run ten and use a fresh filename such as `apinex_prueba_vanilla_11.json` for a later run.

Ninth-run observation: `apinex_prueba_vanilla_9.json` and
`logs/20261021_182928_c61f05bcd469.jsonl` record `failed`, 17 successful calls
(Original 8, Vanilla 9) and 328.235 seconds. Planning passed immediately without needing
normalization. All 13 comments were classified (9 positive, 2 negative, 2 mixed; 0 neutral
or indeterminate). A nonliteral excerpt was corrected on batch attempt two. Vanilla and
Original each had six final-answer rejections and exhausted seven turns; nine of the
twelve rejections were narrative digit matches. Complete evidence was retained but no
independent review ran. These are provisional labels, not validated sentiment accuracy.
The first-stage v3 change above follows this failure; the original artifacts are unchanged.

Offline historical audit: four local artifacts, 13 role executions across Original/Cherry/Vanilla, zero API calls; source review packet at `reports/grounding_audit_before_upgrade.json`. No complete classification labels were preserved in those files, so semantic classifier accuracy is unavailable. Human query/entailment review remains pending; no old narrative result was retroactively certified.

For testing instructions, use [TESTING_AND_RAG.md](TESTING_AND_RAG.md). Run commands from `Agent_Echo/` with the project's Python environment:

```powershell
python -m unittest discover -s tests
python run_agent.py --show-connections
python evaluate_live.py --list
```

The latter two list configuration/cases without making model requests. Live evaluations require an explicitly selected case and configured provider access. Reports and incremental execution logs are local evidence; inspect them before reporting outcomes.

## Decisions, proposals, and pending work

- The sixth run was inspected and motivated the repair above. The user deferred live
  repeats, the full suite, token-limit increases and new agents. Any later authorized live
  comparison must preserve run six and use a fresh artifact filename. The
  [historical command](TESTING_AND_RAG.md#next-live-test-sixth-luna-run) remains a reference.

- Preserve the five-role baseline while evaluating answer quality, usefulness, and provider/model fit.
- The user wants evidence-grounded conclusions and useful partial results when independent findings survive a component failure.
- The existing decision document historically deferred UI and enterprise integration. The group's local UI is now available as recorded above; enterprise integration remains deferred. Dedicated recommendation/planning/execution/monitoring roles are proposals, not implemented agents.
- The existing [brainstorming and decisions document](../echo_brainstorm_resumen_y_decisiones.md), reviewed 2026-10-17, already records architecture, reviewed live examples, limitations, and candidate extensions. It is the detailed source for those discussions; do not present every proposal as approved. This source is present locally but currently ignored by Git, so another checkout may not contain it.
- The current model-selection discussion is exploratory. Compare the same representative HR questions and inspect tool correctness, cited findings, unsupported claims, total task cost, and latency before choosing.

## Reading map and maintenance

| Need | Start here |
| --- | --- |
| Complete reference inventory and maintenance rules | [DOCUMENTATION_MAP.md](DOCUMENTATION_MAP.md) |
| Roles and worked examples | [AGENT_ROLES.md](AGENT_ROLES.md) |
| Scope/review/partial-result behavior | [WORKFLOW_RELIABILITY.md](WORKFLOW_RELIABILITY.md) |
| Setup and live/offline/RAG evaluation | [TESTING_AND_RAG.md](TESTING_AND_RAG.md) |
| Provider assignments and adapters | [connections.json](connections.json), [connections.py](agents/connections.py), [model.py](agents/model.py) |
| Product discussion and proposed extensions | [Existing decisions document](../echo_brainstorm_resumen_y_decisiones.md) |
| Dataset/import documentation | [files_update/README.md](../files_update/README.md) |

Read the orientation documents once per chat when Echo work first becomes relevant, unless their contents are already available in the chat context. Reuse that orientation for subsequent questions; reread only relevant sections if the documents change or verification is needed. Additional source files and other chats are consulted only as needed for the current request.

Update only affected sections after material changes, with a review date and source. Keep live observations separate from planned tests. This file is project documentation, separate from Codex's machine-local generated memories.

Documentation review, 2026-10-21: reconciled setup/profile precedence, selective Lime
execution, batch retries, literal citations, current test history and the next live case
across current guides and local background. Historical classroom inspection dates and
license notices were preserved. This review changed documentation only; no new API call,
runtime feature or measured accuracy result was introduced.
