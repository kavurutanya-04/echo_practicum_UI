# What can be tested without an API, and how to verify RAG

## Next three model runs: 30-32 (2026-10-27)

Current code uses corrected review-v5 and full private capture/checkpoints. No local
tests, build or provider call was run for this update, per user instruction. Static
source parsing/diff/reference review is not runtime validation. New capture/resume
regressions and aligned fixtures are unrun. The 322-test result below belongs to v4.
See [RESUME_AND_CAPTURE.md](RESUME_AND_CAPTURE.md) for the exact scope and retry contract.

Run the following full comparisons once, using new filenames. Do not paste PowerShell's
`>>` continuation markers. This directly uses the existing project interpreter:

```powershell
Set-Location -LiteralPath "C:\Users\percy\Documents\GWU Fall 2026\Practicum\Final_Project\Agent_Echo"

$preguntaPrueba = "I'm preparing for a team check-in. Using all eligible anonymous Recognition survey comments for the third quarter of 2026, classify each comment as positive, negative, neutral, mixed, or indeterminate. Show the count and percentage in each category, including the denominator. Include a short literal excerpt illustrating a positive and a critical view if available, with source citations. Explain the main patterns and interpretation limits, and suggest two follow-up questions for the team. Base this analysis on comment text rather than numerical survey ratings, and do not identify respondents."

# Luna - run 30
& ".\.venv\Scripts\python.exe" run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile apinex_test --run-seconds 1000 --question $preguntaPrueba --output ".\reports\apinex_prueba_vanilla_30.json"

# DeepSeek - run 31
& ".\.venv\Scripts\python.exe" run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile apinex_deepseek_test --run-seconds 1000 --question $preguntaPrueba --output ".\reports\apinex_prueba_deepseek_31.json"

# Gemini - run 32
& ".\.venv\Scripts\python.exe" run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile apinex_gemini_test --run-seconds 1000 --question $preguntaPrueba --output ".\reports\apinex_prueba_gemini_32.json"
```

If a new run fails, retry only its retained phase with live models; do not repeat the
question or full comparison. For example:

```powershell
& ".\.venv\Scripts\python.exe" run_agent.py --resume ".\reports\apinex_prueba_vanilla_30.json" --run-seconds 1000 --output ".\reports\apinex_prueba_vanilla_30_resume_1.json"
```

The failed artifact links its checkpoint. The saved role/profile/scope are used and
must match; a review retry calls only ZeroSugar, then stops at its decision. Each retry
is a new bounded attempt with parent lineage, not an automatic full release or an
unlimited retry loop. Inputs/outputs/arguments, including rejected ones, are retained
in the private capture; existing output files cannot be overwritten. Earlier artifacts
without checkpoints are explicitly rejected rather than silently restarting analysis.

## Assertion-level support review (2026-10-27)

Review-v4 passed all **322 offline tests** with the existing project Python environment.
Nine new tests in test_assertion_review.py cover failed assertions overriding accept,
different source subsets in synthesis, novel proposal reasoning versus factual premises,
live legacy-field bypass rejection, missing/invalid fields/references/textual coverage,
borrowing unrelated sources, Original's repair and two-phase re-review before release,
export versus count-only logging, and legacy reading without invented assessments.
Both contradicted and insufficient_evidence judgments block release. Scripted judgments
verify software behavior, not model accuracy, decomposition or entailment quality.

Initial verification exposed two old fixtures approving unsupported/unknown citations;
demo/test fixtures now supply explicit insufficient_evidence judgments in those cases.
The final full suite passed. The frontend production build passed with its bundle-size
advisory. No browser interaction, new API calls, installation, commit or GitHub push.
The expanded schema has not been exercised against APInex's unchanged 6000-token limit.

Commands run from Agent_Echo (build from Echo_UI/frontend):

```powershell
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests
npm run build
```

Read-only historical checks matched scope/question across runs 15-26, source hashes and
complete label coverage for each stored complete sentiment report, and all structured
visible excerpts against the current database. Counts describe saved labels, not measured
classification accuracy. Run 25 has no complete sentiment report. See the
[history](LIVE_TEST_HISTORY.md) for matching logs, post-run changes and qualitative
comparisons. Preserve saved artifacts and use a fresh filename for any later authorized
live evaluation of review-v4.

## Reasoned actions and review simplification after run twenty-three (2026-10-27)

The approved update makes a reasoned manager action a requirement of complete Original
analysis, independent of whether the prompt requests one. Review instructions separate
factual grounding from novel action reasoning. Support receives the trusted policy flag;
its contextual policy_requirement kind routes repairs without a fabricated user excerpt.

All 88 focused offline checks passed across test_review_contract_v3,
test_review_contract_v2, test_review_stages, test_review_recovery,
test_synthesis_presentation and test_review_field_diagnostics. Four added regressions
cover policy repair routing, contextual-schema isolation, invalid policy origin/ownership
and Original's two-draft repair/review path. Scripted judgments verify software behavior,
not whether a live model identifies a missing action or proposes a useful one. No new
API call, broad suite, UI build or GitHub publication; run twenty-three is pre-change evidence.

## Requested content and additional actions after run twenty-two (2026-10-27)

The approved instruction-only change covers Original and ZeroSugar completeness/support:
requested content and item counts cannot be replaced by useful additional actions;
proposed actions explain their connection to findings and possible benefit. No new
semantic parser, schema or review stage was introduced. All 40 focused offline checks
passed across test_review_stages.py, test_review_contract_v3.py and
test_synthesis_presentation.py. They use scripted judgments and cannot validate live
instruction following or action quality. Run twenty-two is
preserved as pre-change evidence; no new API call or GitHub publication is part of this update.

## Explicit correction judgments after run twenty-one (2026-10-27)

Review-v3 replaces model-managed correction states/replacement graphs with code-keyed
mandatory/addressed judgments and reasons. Canonical correction_reviews and routing remain
compatible. Complete repair text is supplied once, without duplicate prior/completeness
lists. No obligation, source text or semantic judgment is defaulted or sampled away.

147 focused checks passed across test_review_contract_v3, test_review_contract_v2,
test_review_field_diagnostics, test_review_stages, test_review_recovery, test_workflow,
test_flow_improvements and test_provider_connections. New cases cover complete keyed
coverage, strict boolean types, no semantic defaults, optional/false omission withdrawal,
current/inherited state mapping, genuine omissions remaining blocking, explicit duplicate
judgments without replacement graphs, reuse, full repair retention without duplicate
input text, canonical exports and legacy v2 checks. These are software checks, not
measurements of model judgment quality. No complete Original rerun, broad suite or UI build.

Live diagnostics are retained locally. The first manual recheck did not load trusted
source documents and is invalid for analytical evaluation; its artifact/log are retained
as reports/review_v3_check_21_20261027.json and 20261027_135536_e0e4fa77d3e7.jsonl.
It made four successful calls but failed on an omitted required judgment field. The
corrected-source recheck made two calls (one successful adapter response); completeness
completed, but support reached 6000 output tokens, finish_reason=length, and was withheld.
Evidence: reports/review_v3_check_21_20261027_verified_sources.json and
20261027_142055_e77b6010b76f.jsonl. Neither result establishes a semantic improvement.
The compact-input prototype completed a support response but again omitted required;
its two-call cap stopped further repair. Evidence: reports/review_v3_check_21_20261027_compact_input.json
and 20261027_143156_4cc85f95fd1a.jsonl. The field was renamed mandatory to distinguish
the semantic judgment from JSON Schema's required metadata; this does not establish that
APInex strips keyword-named properties. Per-judgment reasons are now bounded to 300
characters and validated against that same schema limit. A two-call recheck then spent
both calls on completeness (an exact-excerpt repair) and never exercised support:
reports/review_v3_check_21_20261027_mandatory_field.json / 20261027_143645_0e172863a009.jsonl.

The final support-only check reused the completed completeness review from run twenty-one
after verifying identical answer/evidence/chart identity. It loaded all trusted scoped
sources and assessed all 16 obligations in one live call. It completed review-v3 with no
rejections or deterministic issues: six withdrawn obligations, ten retained and one new
correction (eleven pending), decision revise. It used 16541 input / 3515 output tokens
(2528 reported reasoning tokens) under the same 6000 output limit. Evidence:
reports/review_v3_check_21_20261027_support_only.json and
20261027_144043_c31c613c57d1.jsonl. This proves the observed support-contract execution,
not that both phases were newly run or that its semantic judgments were correct. The
model still incorrectly demanded another denominator sentence and retained redundant
work. No full Original workflow was rerun. Across all retained attempts in this update,
11 provider requests were made; 10 passed adapter completion checks. Failed attempts
are not analytical success. No budgets or provider settings were raised.

## Contextual-field update after run eighteen (2026-10-26)

Implemented without executing tests, model calls, builds, commit or push. Focused checks
were added for omitted inactive fields with empty exported assessments, ignored invented
inactive entries with metadata-only diagnostics, mandatory active assessments and schema
rebuilding when reusing a reviewer. Existing retry/field-diagnostic fixtures now omit an
essential finding_reviews field rather than an inactive numeric_reviews field.

These checks are unrun; historical test counts do not validate this update. Run eighteen
exercised the preceding version. Preserve its artifact/log; use a fresh filename such as
`reports/apinex_prueba_vanilla_19.json` for a future authorized live run. See the
[current contract](WORKFLOW_RELIABILITY.md#contextual-support-review-fields-after-run-eighteen-2026-10-26).

## General-guidance update after run seventeen (2026-10-26)

Implemented shared rubric v3 and removed case-specific live guidance. Existing correction
fixtures were aligned with required literal request excerpts and retention, including
nested-field diagnostics. Existing sentiment assertions now cover the current version,
historical v1/v2 identity, unversioned v1 fallback and full canonical source coverage.
None were executed. No provider calls, UI build, commit or push were performed.

Earlier test counts do not validate this update. Run seventeen completed under v2 with
13 included comments and both reviews; its successful operation does not establish
semantic accuracy or validate v3. Preserve it and use a fresh artifact such as
`reports/apinex_prueba_vanilla_18.json` for a later authorized live evaluation. See the
[current contract](WORKFLOW_RELIABILITY.md#general-semantic-guidance-after-run-seventeen-2026-10-26).

## Semantic-review update after run sixteen (2026-10-26)

The user authorized implementation without tests or GitHub publication. No tests, provider
calls, UI build, commit or push were run for this update. Earlier test counts below do
not validate the shared v2 sentiment rubric, retained correction request excerpts or the
full classification review input. Existing review fixtures that omit request_excerpt in
new-style corrections or expected its removal were still unaligned at that point; the
subsequent run-seventeen follow-up above aligns them without executing tests.

The preceding run sixteen completed with two candidates and both final review phases,
but accepted incorrect sentiment reasoning and unnecessary requirements. Its sources,
coverage, literal quotes and aggregates were checked read-only; semantic label quality
remains unvalidated. Preserve its artifact and log. A future authorized live evaluation
must use a fresh filename such as `reports/apinex_prueba_vanilla_17.json`.

Pending validation: new versus legacy correction schemas and literal excerpt retention;
v1 replay versus stored v2 rubric identity; complete released-group source/label input
without suppressed texts, scores or identity fields; metadata-only coverage diagnostics;
input-size failure without sampling; unchanged two-phase acceptance and shared budgets.
Human-referenced semantic cases must distinguish full coverage with indeterminate labels,
mixed evaluations with a favorable overall verdict, positive continuation requests,
explicit denominators, valid source IDs and unrequested category examples. Scripted
fixtures cannot demonstrate model judgment. See the
[implementation contract](WORKFLOW_RELIABILITY.md#sentiment-and-correction-grounding-after-run-sixteen-2026-10-26).

## Review recovery checks (2026-10-26)

The approved four-draft follow-up passed **292 offline tests** on Windows with the
existing Python 3.12.10 environment. Three additional regressions confirm acceptance
on draft four after three rejected candidates, recovery after the second and third
incomplete support reviews, and shared-call-budget termination before four drafts
without approval. Repeated-failure fixtures now cover four drafts and no fifth attempt;
early acceptance, unsafe-output withholding and chart-only reuse remain covered.
ZeroSugar still has three submission attempts per phase. The 61 review-focused tests
also passed. This update remains local, without provider calls, commit or GitHub push.

Before that follow-up, the review-recovery update passed **289 offline tests** with the existing
Python **3.12.10** environment. Ten new tests in `tests/test_review_recovery.py` exercise
optional annotation normalization without fabricated judgments, malformed suggestion
isolation, essential-field rejection, clarification requirements, withdrawal of a false
omission while retaining a real one, current-correction identity/state diagnostics,
trusted-scope isolation, repair instructions without a verdict, recovery into two new
completed review phases, withholding after repeated failure, and provider-failure isolation.
The 58 review-focused tests also passed separately. Existing tests were updated for
trusted authorization input and conservative obligation retention; essential field-error
capture remains covered. These use scripted judgments, not measured model accuracy.

Commands run from `Agent_Echo`:

```powershell
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_review*.py'
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests
```

No live calls, provider/strict-mode changes, budget increases, UI build or GitHub push
are included. Use a fresh filename, such as `apinex_prueba_vanilla_16.json`, for the next
authorized live test; preserve the repeat-run-fifteen artifact and its matching log.
Acceptance still requires complete independent review and source checks. See the
[recovery contract](WORKFLOW_RELIABILITY.md#review-recovery-after-run-fifteen-2026-10-26).

## Field-error diagnostic checks (2026-10-26)

The diagnostic-only follow-up passed the full **279-test offline suite** on Windows,
using the existing Python **3.12.10** environment. Nine new regressions in
`tests/test_review_field_diagnostics.py` cover missing/additional root fields, wrong
root types, nested paths/indexes, comparison with the actual declared schema, both
review phases, repeated versus changed conditions, explicit repair events, artifact/log/
feedback delivery, invalid-submission withholding and bounded/redacted field names.
A malformed key containing source prose is fingerprinted rather than copied to logs.
Values from rejected fields are omitted. The tests use scripted responses, not APInex.

Command actually run from `Agent_Echo`:

```powershell
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests
```

The nine focused regressions also passed separately. Python source syntax and changed
Markdown link paths were checked. No live-provider calls, model changes, strict-mode
activation, UI rebuild or new semantic review rules were part of this follow-up.
Use a fresh artifact for later live diagnosis; run fourteen's old missing/extra keys
cannot be reconstructed from its retained generic errors.
See the [diagnostic contract](WORKFLOW_RELIABILITY.md#field-error-diagnostics-follow-up-2026-10-26).

## Review/data update validation (2026-10-26)

The full offline agent suite passed **270 tests** on Windows with the existing
`Agent_Echo/.venv` Python **3.12.10**. Twenty new regressions cover review-v2 obligation
coverage, withdrawal/consolidation, real visible omissions, precise structural feedback,
metric relevance/retirement, phase persistence, reviewed-version partial release,
manager payload redaction, origin-neutral chart export and v3/v4 replay. The scripted
revision fixture now explicitly assesses its prior corrections; the default-version
assertion now expects v4. Scripted judgments test contracts, not semantic accuracy.

Commands actually run from `Agent_Echo`:

```powershell
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests
```

The existing frontend dependencies built successfully with `npm run build` from
`Echo_UI/frontend` (TypeScript and production bundling). Python source syntax checks
passed for agents and UI backend. Payload-boundary tests execute the actual pure backend
helpers without starting a server or reading credentials. No browser interaction,
server restart, dependency installation or live-provider request was performed.

The stored v3 text AND claims in `apinex_prueba_vanilla_12.json` and
`apinex_prueba_vanilla_13.json` reproduced exactly with the new code; both local artifacts
remain unchanged. This replay proves compatibility, not that their labels are correct.
Use a fresh filename for a later authorized live evaluation. Confirm complete reviews,
visible requested examples, actual source support, relevant calculations and the final
version displayed. Human classifier evaluation remains separate.

Updated 2026-10-26. Run commands inside `Final_Project/Agent_Echo` with the project's Python environment. `.env.example` is a reference; live clients load only keys from the private, Git-ignored `.env` or process environment. Models, endpoints, API versions, limits and role selection are in `connections.json`; `--profile` is an explicit per-run selection. Never put real keys in files committed to Git. GW Azure is the primary/final provider; all other profiles are optional tests.

Earlier focused update, 2026-10-26: the audit follow-up covers mandatory assessment of
pending corrections, configured Responses output limits and Chat deadline checks before
explicit HTTP attempts, including after pacing/retry waits. Eight new regressions use
scripted responses, fake clients and a fake clock; old revision/demo fixtures now explicitly
assess their pending corrections. No provider request or full-suite run is part of this
follow-up. All 121 focused checks passed on Windows Python 3.12.14 and cover these six modules:

```powershell
$checks = 'test_review_stages.py', 'test_provider_connections.py', 'test_request_pacing.py', 'test_workflow.py', 'test_sentiment_workflow_repairs.py', 'test_visuals_rag.py'
foreach ($check in $checks) {
    ..\Echo_UI\.venv-windows\Scripts\python.exe -B -m unittest discover -s tests -p $check
    if ($LASTEXITCODE -ne 0) { throw "Focused check failed: $check" }
}
```

See the [workflow follow-up](WORKFLOW_RELIABILITY.md#audit-follow-up-review-coverage-output-limits-and-request-deadlines-2026-10-26).

Historical full-suite update, 2026-10-23: the selected autonomy/two-stage review changes passed the full
242-test offline agent suite, including 19 new tests in `tests/test_review_stages.py`.
The initial baseline had 15 failures and 4 errors in 223 tests; historical v2 checks and
older normalization/provider-log expectations were aligned with their actual contracts,
and partial-output compatibility was fixed. Current v3 signals and explicit quote checks
are covered separately. No API/model/embedding call was run. Scripted review decisions
verify isolation and release mechanics, not model compliance or classifier accuracy.

Tests cover evidence isolation in the first review, independent support rejection,
nonblocking style suggestions, finding-ID citation attachment, bounded phase retries,
shared model/tool limits, failed phase statuses, redacted metadata, actual pending-item
continuity, legacy checklist input and current/historical grounding contracts. Windows
Python 3.12.14 was used from the existing UI environment, without installing dependencies:

```powershell
..\Echo_UI\.venv-windows\Scripts\python.exe -B -m unittest discover -s tests
```

The additional completeness call consumes the existing shared call/time budgets. GitHub
publication is authorized after validation. Preserve run eleven and use a fresh artifact
such as `reports/apinex_prueba_vanilla_12.json` for a later authorized live evaluation.
See the [current workflow](WORKFLOW_RELIABILITY.md#autonomous-synthesis-and-two-stage-review-2026-10-23).

Historical update, 2026-10-22: requested-deliverable coordination and explicit corrections
retain source-facts-v3 and specialist formats. No tests, saved-artifact replay or provider
calls were run, by user instruction; GitHub publication was initially deferred and later
authorized separately (see PROJECT_CONTEXT.md). Static review
does not establish model compliance. Later validation should cover numeric-only, text-only,
mixed and standalone specialist paths; retained examples missing from visible answers;
all prior corrections resolved/unresolved; optional wording suggestions; runtime coverage
failures; legacy review/plan fields; and complete-package review after a localized edit.
The new response fields add structural work within the existing call/attempt budgets;
their provider compliance and token cost remain unmeasured. See the
[coordination contract](WORKFLOW_RELIABILITY.md#requested-deliverables-and-explicit-corrections-2026-10-22).
Preserve run ten and use a fresh filename, e.g. `reports/apinex_prueba_vanilla_11.json`,
for a later authorized live attempt.

Static-only evidence for this update: four changed Python sources parsed without importing
the application; local link targets in eight affected guides existed; the new coordination
heading was present; the whitespace/diff check was clean. These are not runtime tests.

Historical v3 update, 2026-10-21: `source-facts-v3` turns narrative digit/quantifier rejections into review
signals, normalizes unambiguous presentation, permits row/single-source interpretations
without quotes, and retains bounded redacted diagnostic context. Per user instruction,
no local tests, saved-artifact replay or live/provider calls were run for this update.
Only static source/syntax/diff review is permitted in this task. All test counts below
are historical and do not validate v3; existing assertions about default numeric rejection,
single-source mandatory quotes and minimized narrative omission describe the old contract.
Saved v1/v2 replay branches remain implemented. The then-proposed tenth run has since
been inspected; its result predates the coordination update and is recorded in PROJECT_CONTEXT.md.
Completion requires an actual completed independent review and requested answer coverage,
not merely successful provider calls. See
[v3 workflow](WORKFLOW_RELIABILITY.md#narrative-review-signals-and-presentation-v3-2026-10-21).
Static evidence for that 2026-10-21 update: Python's syntax parser accepted all seven changed Python
files without importing the application; the staged whitespace/diff check was clean.
Neither activity executes a test or demonstrates model behavior.

Use [DOCUMENTATION_MAP.md](DOCUMENTATION_MAP.md) to navigate all references and
[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for dated observations. The 207-test result
below belongs to an earlier implementation check, not the current v3 update.

Historical v2 synthesis/presentation update, 2026-10-21: only focused final offline checks were requested.
The new cases in `tests/test_synthesis_presentation.py` cover multi-source synthesis,
individual literal quotes, retained numeric restrictions, table/cell repetition, v1
replay, optional suggestions and mandatory/source-integrity failures. Existing focused
grounding/recovery checks remain applicable. No initial baseline, full suite or live call
is part of this update; scripted reviewers do not establish real model quality.
Final checks passed: **36 focused offline tests** (`test_synthesis_presentation.py`: 8;
`test_grounded_claims.py`: 20; `test_recovery_feedback.py`: 8). A read-only replay of run
seven's saved v1 candidate reported no claim-audit issues. Rendering its same selection
through v2 reduced 21 blocks to 10 by removing the 11 repeated cells; this is a renderer
check, not a new model answer or live approval. No original artifact was overwritten.

## Three different activities

For evaluating intelligence, use the live evaluation cases after configuring a provider. Running Python locally can still call a cloud LLM; the decisive distinction is live API responses versus programmed fixtures. The demo is an optional engineering diagnostic, not a reasoning benchmark. Provider access and analytic quality require separate checks; see the NVIDIA/OpenCode access findings below.

| Activity | Calls an API? | What the result establishes |
| --- | --- | --- |
| Unit/integration tests and `--demo` | No; scripted/mocked responses | Queries, restrictions, retrieval plumbing, rendering, review gates and error handling work on those cases. It does not evaluate LLM reasoning, chart selection or answer quality. |
| `inspect_rag.py --retrieval lexical` | No | Real local passages can be retrieved with source IDs and scope. No generated answer is produced. |
| Live agents / `--check-connection` / `evaluate_live.py` | Yes; configured credentials required | A real provider is called. Connection success does not establish analytic accuracy; full answers still need independent review. |

Semantic/hybrid retrieval additionally calls a configured **embedding API**, even when no answer is generated. Generation and embedding configuration are separate.

Without credentials you cannot evaluate a real LLM answer. Live commands fail with missing variable names and never silently switch to the demo. The demo ignores an arbitrary `--question` and uses a fixed scripted scenario. Its judge scores and Lime decisions are fixtures.

## 1. Run offline engineering checks

The current live answer contract and historical-output audit are documented in
[SOURCE_GROUNDING.md](SOURCE_GROUNDING.md). Focused regression checks use no provider:

```powershell
python -m unittest discover -s tests -p test_grounded_claims.py -v
python -m unittest discover -s tests -p test_clarification_policy.py -v
python -m unittest discover -s tests -p test_rejection_diagnostics.py -v
python audit_grounding.py reports/apinex_prueba_media_actualizada.json --output reports/grounding_review.json
```

The audit packet requires human review of entailment, query meaning and label semantics;
it does not report accuracy from an unannotated sample. Live runs now require a final
`submit_grounded_answer` selection from the source catalog instead of free-form factual prose.

Shared-rule and clarification regressions cover the complete medium question, unnecessary
clarification repair, genuine ambiguity, already supplied scope, invalid quoted request
excerpts, bounded failures, shared budgets, safe diagnostics and every analysis call path.
They also check that a normal plan adds no reconsideration call. These are scripted
engineering checks, not proof that Luna always recognizes ambiguity correctly. See
[shared rules and clarification handling](WORKFLOW_RELIABILITY.md#shared-rules-and-initial-planning-clarifications-2026-10-21).
The historical local suite passed 207 tests on 2026-10-21, including 16 policy/clarification,
15 rejection-diagnostic and 22 sentiment-workflow regressions, with zero generation API calls.
The user's fourth live Luna run completed with nine successful calls and source-matching
results; it also exposed four corrected source-submission rejections. The diagnostic
update followed that run; the fifth run exercised it but failed before review. Its offline
replay reproduces that run's accepted answer/claims exactly. New checks verify granular
causes, minimal-fragment retention, omission of sensitive-looking input, success/failure
persistence and review-round continuity. See
[rejected source-answer diagnostics](WORKFLOW_RELIABILITY.md#rejected-source-answer-diagnostics-2026-10-21).
Preserve earlier artifacts and use a new output filename for subsequent live tests.
Terminal clarification still prints the question and exits; interactive continuation is deferred.

The fifth Luna run failed with 28 successful calls and zero ZeroSugar calls: incorrect
specialist routing, restarted classification and unavailable individual comment sources
prevented release. The subsequent repair has only offline coverage. Its focused checks
use prescribed labels with the actual scoped test documents to exercise third-attempt
repair, non-resetting counters, safe incomplete outcomes, early declines/reassignment,
canonical comment evidence, independent replay and CLI status. Run from `Agent_Echo/`:

```powershell
python -m unittest discover -s tests -p test_sentiment_workflow_repairs.py -v
```

The next real test should repeat the fifth Recognition-comments question with a new
artifact filename. Confirm Vanilla's completed coverage, exact excerpts, individual text
sources, actual ZeroSugar review, preserved diagnostics and total calls/tokens. Unchanged
20-second pacing and shared budgets still apply. A passing scripted workflow is not proof
that Luna will choose the correct tools or sentiment labels.

```powershell
python -m unittest discover -s tests -v
python .\run_agent.py original --manager M14 --demo --output .\reports\offline_workflow.json
```

The terminal explicitly reports `OFFLINE SCRIPTED FIXTURE` and zero generation API calls. The JSON labels the mode, holds actual SQL/text evidence and records fixture review/visualization. SVG/CSV files use the real local query rows, but the decision to plot and the written explanation are programmed. Do not report fixture scores as model accuracy.

## 2. Inspect retrieval without generating an answer

```powershell
python .\inspect_rag.py --manager M14 --start 2026-07-01 --end 2026-09-30 --query "recognition contributions acknowledge" --source HR_survey_comments --dimension Recognition --limit 4 --output .\reports\retrieval_only.json
```

Check `retrieval`, `metadata.query`, filters, `corpus_records`, `returned_count`, actual `passages`, dates and `citation_id`. Lexical hits include BM25 scores; lower scores rank first. This command labels `generation_performed=false`. Read the returned passages: matching vocabulary does not guarantee that the passage answers the question.

## 3. Configure and probe a real connection

Start with the **primary GW Azure** connection when the professor provides your group's access. Put only `GW_AZURE_OPENAI_KEY` in the private `.env`. Set the assigned `endpoint`, deployment `model` and `api_version` in the `gw_azure` JSON profile. Use only your group's assigned resource and key; obtain the deployment name from that resource or the professor rather than guessing from the example notebook. API keys stay local and are not committed. JSON contains the non-secret connection settings; unavailable deployment and endpoint values remain empty.

```powershell
python .\run_agent.py --check-connection --profile gw_azure
```

The explicit `--profile gw_azure` uses the same GW deployment for every role, overriding temporary test assignments. No other provider keys are required, and a missing GW setup never falls back to a trial API. If a collaborator already has the API key in their process environment, no `.env` file is needed; non-secret settings still come from JSON.

For NVIDIA/OpenCode, paste only the keys into the private `.env` beside `connections.json`:

```dotenv
NVIDIA_API_KEY=
OPENCODE_API_KEY=
```

The models/endpoints are configured, but live access is not guaranteed. Both NVIDIA profiles use the same `NVIDIA_API_KEY`. On 2026-10-16 OpenCode rejected external free-tier Python requests with HTTP 403 `FreeTierError`, NVIDIA GLM timed out, and NVIDIA Nemotron Ultra returned HTTP 404. Do not present these as working live connections. The OpenCode command below remains an access diagnostic, not a recommendation to use its free tier for Echo. Run the probes separately:

Historical follow-up, 2026-10-16: `nvidia_test` used `nvidia/nemotron-3-super-120b-a12b`, which the user reported answered a plain text request. Both NVIDIA profiles retain 8192 output tokens, with `timeout_seconds=120` and `max_retries=0`. The GLM default retains NVIDIA's documented reasoning settings; a plain diagnostic can omit them in memory. Text completion, tool-call confirmation and full analytic quality are distinct checks. Earlier Echo timeouts occurred with 8192 tokens, so the user's separate 20-token experiments do not establish their cause. `finish_reason=length` now produces an explicit output-token-limit error. Those historical model/endpoint overrides have been removed by the configuration standardization; use the JSON profile instead.

Current configuration, 2026-10-20: `nvidia_test` now selects `nvidia/nemotron-3.5-super-vl-120b-a12b` because NVIDIA deprecated the old Super free endpoint. The new model has a documented free Chat Completions endpoint. The October 16 results below belong to the old model; they are not validation of the new model. Edit the JSON profile to change the model; old `.env` and terminal model overrides are not used.

New-model validation, 2026-10-20: the connection probe passed with `nvidia/nemotron-3.5-super-vl-120b-a12b`, using one real tool call for the shared profile. The ignored local log is `reports/logs/20261020_213401_ec97b74226cb.jsonl`. This establishes connection and minimal tool support; a real manager-question evaluation is still separate. The 19 provider-connection tests also passed.

```powershell
python .\run_agent.py --check-connection --profile nvidia_test
python .\run_agent.py --check-connection --profile nvidia_glm_test
python .\run_agent.py --check-connection --profile opencode_test
```

Follow-up live probes on 2026-10-16 confirmed one real tool call with Nemotron Super, one with GLM-5.3-Flash using a plain request without reasoning options, and one using the configured GLM reasoning options. Both GLM probes took close to two minutes; the configured defaults are retained. Minimal tool access now works for the tested account, but latency and continued availability remain unconfirmed beyond these individual requests. These are minimal API/tool checks, not completed manager analyses. The earlier failures remain historical observations; local logs preserve the follow-up results.

Environment keys take precedence over `.env`. Only live client construction can read that file; inspection and scripted demos do not. New collaborators can copy `.env.example` to a new local `.env` and insert their own keys; `.env` never needs to be shared. If the keys already exist as terminal/system environment variables, no `.env` is required. The shared default is still `gw_azure`, so select a test profile explicitly. These profiles use no paid-model fallback. Check the provider's current free access and limits; the application does not monitor pricing changes.

To test several models in one workflow, assign profiles per role in `connections.json`, as shown in [README.md](README.md#one-connection-layer-selectable-profiles-per-agent). Run `--show-connections` and then `--check-connection` without `--profile` to preserve those mixed assignments. Supplying `--profile` intentionally forces one model profile for all roles. The probe checks each distinct assigned profile once, even if several roles share it.

Inspect assignments first; this does not test the API:

```powershell
python .\run_agent.py --show-connections --profile google_test
```

For Google, set the model and endpoint in the `google_test` JSON profile, then securely enter only the key in the terminal:

```powershell
$env:GOOGLE_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Google API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile google_test
```

For the assigned GW Azure resource, configure `profiles.gw_azure.endpoint` and `model` in JSON first:

```powershell
$env:GW_AZURE_OPENAI_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "GW Azure API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile gw_azure
```

For personal OpenAI, set `profiles.personal_openai.model` and its explicit endpoint in JSON, put `OPENAI_API_KEY` in `.env` or the process environment, and select `--profile personal_openai`. Do not guess deployment availability from the existence of a profile or university account.

The probe makes one actual minimal function call per distinct selected generation profile. A shared profile is tested once and mapped to each role. It supplies no employee data. It does not test embeddings or prove that any analytic answer is correct. No connection was exercised against a real provider during this implementation update.

### APInex SDK trial

Added 2026-10-27 from the user's examples: `apinex_deepseek_test` selects
`free/deepseek-v4.1-flash`; `apinex_gemini_test` selects `free/gemini-3.8-flash`.
Both reuse the APInex Chat endpoint/key variable and Luna's limits, pacing and retry
settings. Existing profiles, default and role assignments remain unchanged. Inspect
either with `python .\run_agent.py --show-connections --profile PROFILE_NAME`.
Both CLI selections were checked for all five roles, with existing profiles/defaults
preserved, and all 26 existing provider-connection tests passed offline. These checks
do not establish live tool support or answer quality; no API call was made for these additions.

The optional `apinex_test` profile uses the existing OpenAI-compatible Chat Completions adapter, base URL `https://api.apinex.bond/v1`, and model ID `free/gpt-6-luna` from the user's APInex setup page. The SDK appends `/chat/completions`; do not add that path to the base URL. APInex's [public API reference](https://apinex.bond/developers) documents this endpoint. This is an Echo Python integration; the site's Codex `/responses` instructions configure a different client.

#### Strict Chat transport follow-up, 2026-10-27

ChatModel previously dropped the strict flag declared by function_tool. It now forwards
explicit true/false values within the Chat function definition, preserving absent values
and the original tool objects. Three focused offline adapter checks passed (strict
forwarding, tool-history round trip and configured trial routing). Thirteen object-schema
declarations were checked for complete required fields and additionalProperties=false;
this is a structural audit, not certification of every provider's schema subset.

Two successful live requests used apinex_test/free/gpt-6-luna, with no employee data:
the existing connection check and a synthetic fixture using ZeroSugar's actual nested
support schema, including ratings, corrections, correction states and numeric reviews.
The synthetic request captured strict=true at the SDK boundary; the response conformed
to its schema and exactly matched the fixture. Local metadata evidence is
reports/strict_transport_probe_20261027.json; logs are
20261027_061516_7cc233292e46.jsonl and 20261027_061641_f1a8f52f745b.jsonl.
An earlier restricted-network attempt failed; the network-enabled retry succeeded.

APInex's [structured-output guide](https://apinex.bond/guides/structured-json-output-llm-production)
declares strict tool support, but these observations do not prove server-side constrained
decoding, semantic accuracy, other providers' compatibility or resolution of run nineteen.
The correction protocol and two review phases remain unchanged. No full suite, complete
analytic rerun or GitHub publication was performed. Historical trial results below retain
their original dates and limits.

#### Single-call review follow-up after run twenty, 2026-10-27

Run twenty failed in completeness after a rejected rationale and two duplicate-call
responses. ChatModel now requests parallel_tool_calls=false only for one required tool;
other tool modes retain their existing behavior. Existing cardinality/release gates
remain. Rationale failures include expected/actual types, max_characters and string
actual_characters in artifacts, logs and repair feedback; rejected text is not retained.

Focused offline results: 26 provider-connection tests and 10 review-field-diagnostic
tests passed, including the new request-mode and private-content regressions. One live
APInex call rechecked only the saved run-twenty completeness phase with its real visible
answer and scope. SDK-boundary capture confirmed strict=true and parallel_tool_calls=false;
the response contained one call and completed the phase with revise, score 2, a
752-character rationale and two corrections. Semantic correctness of that verdict was
not established; support review and complete release were not exercised. Evidence:
reports/completeness_transport_check_20_20261027.json and
reports/logs/20261027_063645_1ecd888e5f0a.jsonl. No full workflow rerun or publication.

Put only a fresh key in the ignored local `.env` beside `connections.json`:

```dotenv
APINEX_API_KEY=your_new_key_here
```

Keep the model and endpoint in `connections.json`. Revoke any key exposed in chat before entering its replacement locally. Inspect the profile without API access, then run the tool-call probe after adding the key:

```powershell
python .\run_agent.py --show-connections --profile apinex_test
python .\run_agent.py --check-connection --profile apinex_test
```

The setup page supplied on 2026-10-20 states 5 requests/minute for free access and 30 with a subscription. The user selected one model, Luna, for all five roles and a conservative target of 3 requests/minute. `apinex_test` sets `request_interval_seconds=20` and `rate_limit_retries=2`. One process-wide pacer is shared by roles and registries using the same endpoint and credential, including HTTP 429 retries. It spaces actual request starts, honors a valid `Retry-After` (seconds or HTTP date) when longer than its fallback, and otherwise backs off 20 then 40 seconds before its two retries. Exhaustion still reports the existing safe HTTP error; the cooldown remains shared. SDK `max_retries=0` prevents hidden retries from bypassing pacing. Execution API-call counters include these actual retry attempts. Wait/retry events record timing only, without keys or response payloads. Separate terminal processes or other applications using the key are not coordinated by this in-process pacer.

The existing workflow defaults remain 32 model turns, 48 local tool calls and 300 seconds elapsed time; specialist loops also have their own turn bounds. These prevent runaway loops and are distinct from requests/minute. HTTP retries count in execution API-call totals, not as new logical workflow turns. Deliberate pacing waits consume elapsed time. For a longer Original/Vanilla run, explicitly add `--run-seconds 900` (15 minutes); this does not increase the model-turn limit. Since 2026-10-26, budgeted Chat calls also check the deadline before each adapter-controlled HTTP attempt and after pacing waits, refusing to send once it expires. In-flight requests and waits are not forcibly cancelled; SDK-internal retries retain their existing settings.

The minimal probe confirmed one real Luna tool call on 2026-10-20, not analytical quality
or sustained throughput. The first medium run failed after 17 calls. After subsequent
repairs, the fourth run completed its numeric comparison with nine calls; the fifth
comment run failed after 28 calls before ZeroSugar. The shared default remains `gw_azure`;
`--profile apinex_test` selects Luna for every role. The profile allows at most 6000
output tokens per request, raised from 3500. That is a maximum, not a requested response
size. The latest sentiment repairs still require their own real follow-up.

The 2026-10-20 workflow corrections support multiple planned metrics, retain Cherry's query tools, expose numeric task coverage, allow literal sentiment excerpts up to 400 characters, repair only invalid records within a classification batch, and identify structured review errors by field/code. Run the focused regression checks without a model or API:

```powershell
python -m unittest discover -s tests -p test_workflow_repairs.py -v
```

Then run the full suite when implementation changes warrant it. Prescribed model
responses test software contracts, not model reasoning. The next real follow-up targets
the fifth comment-classification case below; preserve all earlier artifacts. Run only one
terminal process per key because pacing is shared within a process.

### Next live test: sixth Luna run

Status update, 2026-10-21: the user executed the historical command below. The saved run
failed after complete classification, before ZeroSugar. Preserve that sixth-run artifact;
use a new output filename for any future authorized repeat. The current repair runs only
focused offline checks, with no full-suite rerun or provider requests. APInex remains at
6000 output tokens; raising limits and changing provider configuration are out of scope.

Focused repair verification: **75 offline tests passed** across
`test_recovery_feedback.py` (8), `test_rejection_diagnostics.py` (15),
`test_workflow_repairs.py` (10), `test_grounded_claims.py` (20), and
`test_sentiment_workflow_repairs.py` (22). These check temporal references, numeric
restrictions, citation positions/privacy, repeated feedback, Cherry/Vanilla evidence
recovery through review, failed/unexecuted reviews, Lime repair and truncated-output
counter logging. No full-suite baseline rerun or live API call was made. Scripted
responses establish these software contracts, not future model compliance or label quality.

Open `Final_Project` in VS Code. In a terminal at that repository root, with the existing
Conda environment available, run this block. If the terminal is already inside
`Agent_Echo`, omit the `Set-Location` line. A new clone can use the virtual environment
instructions in the root README instead of Conda.

```powershell
Set-Location -LiteralPath .\Agent_Echo
conda activate echo-agent
python run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile apinex_test --run-seconds 1000 --question "I'm preparing for a team check-in. Using all eligible anonymous Recognition survey comments for the third quarter of 2026, classify each comment as positive, negative, neutral, mixed, or indeterminate. Show the count and percentage in each category, including the denominator. Include a short literal excerpt illustrating a positive and a critical view if available, with source citations. Explain the main patterns and interpretation limits, and suggest two follow-up questions for the team. Base this analysis on comment text rather than numerical survey ratings, and do not identify respondents." --output .\reports\apinex_prueba_vanilla_6.json
```

The question, manager and dates match run five; only the output filename changes. Check
whether this file already exists before a later repeat, since `--output` overwrites it.
The earlier documentation review had not found the sixth-run result; it has now been inspected.
Inspect both the JSON and the exact `.jsonl` path printed at startup; a complete result
still does not measure human-validated sentiment accuracy.

## 4. Run a live answer with lexical RAG

```powershell
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --question "Review recognition using quarterly survey metrics and supportive and critical anonymous comments. Include an indicator chart if supported." --output .\reports\live_review.json
```

Omit `--demo`: this is essential. All five model roles use the selected profile. The workflow runs Lime for each candidate and ZeroSugar reviews the answer/chart plan before local export. `execution.successful_generation_api_calls` counts successful adapter requests; `profiles_used` records the actual model/deployment names. The offline value is always zero.

## 5. Test semantic/hybrid RAG aligned with the classroom notebook

Configure `profiles.google_embeddings.model` in `connections.json` with an embedding model actually available to the same Google account:

```powershell
python .\inspect_rag.py --manager M14 --query "recognition of work contributed to another team" --retrieval semantic --embedding-profile google_embeddings --limit 4 --output .\reports\semantic_retrieval.json
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --retrieval hybrid --embedding-profile google_embeddings --question "What recognition metrics and anonymous comments support a manager follow-up?" --output .\reports\hybrid_review.json
```

Azure uses the `gw_embeddings` JSON profile; personal OpenAI uses `openai_embeddings`. Set the corresponding `model` and `endpoint` in JSON. Start with one quarter: initial document embedding can make many requests and sends scoped passage text to the selected provider. Local caches reuse document vectors but query embeddings still require the provider. There is no automatic semantic-to-lexical fallback.

## How to demonstrate RAG rather than just claim it

The actual path is `ScopedData.text_documents` -> `TextSearch` or `SemanticTextSearch` -> `search_text` result -> tool-result context in the next `model.respond` -> cited Vanilla answer -> ZeroSugar source checks. This is the classroom retrieval/context/generation pattern implemented with function tools.

Inspect a saved Original artifact:

1. Find the Vanilla entry in `delegations` and its `tool_trace` search calls. Confirm queries, filters, retrieval method, passage text and citation IDs.
2. Check `rag.specialist_runs`: `context_supplied_to_generator`, returned IDs, `cited_ids` and `generation_mode`. Direct Vanilla runs store the same information directly in `rag`.
3. In semantic/hybrid results, inspect embedding identity, cosine scores and ranking method. Scores are retrieval ordering, not confidence or prevalence.
4. Match answer claims to the passages themselves and independently check relevance/entailment. Citation existence alone is insufficient.
5. Confirm live mode and successful generation API calls. An offline fixture can demonstrate that context reaches a simulated call, but is not proof of live grounded reasoning.

RAG is not necessarily used on every Original run: a purely numerical question can use Cherry alone. An empty search is recorded with no returned IDs and `context_supplied_to_generator=false`; do not describe that as a grounded textual answer. SQL evidence is structured grounding, distinct from Vanilla's textual RAG. Systematic sentiment classification enumerates the full eligible population rather than ranking passages; it is recorded separately in `sentiment`, not misrepresented as ranked textual RAG.

## Sentiment implementation versus model quality

The `survey_sentiment` live case asks Original for Recognition sentiment percentages in one quarter. Confirm that Vanilla actually calls `analyze_survey_sentiment`, covers all eligible IDs, preserves per-comment labels/excerpts/source hashes, includes mixed/indeterminate in the denominator and discloses `human_validated=false`. ZeroSugar must recompute the summary and reject altered counts or source provenance. Source lookup and aggregation validation cannot establish the semantic accuracy of every model label.

Offline sentiment tests use prescribed labels solely to check those contracts, batch completeness, failures, privacy fields and arithmetic. They do not evaluate intelligence. The fifth live run's complete child report was never independently reviewed or released. Human quality evaluation must use independently annotated held-out comments across categories/dimensions, per-category precision/recall, a confusion matrix and inspection of ambiguous/mixed cases. No independently measured classifier quality result is available.

## Fixed live evaluation cases

```powershell
python .\evaluate_live.py --list
python .\evaluate_live.py --case recognition_counts --profile google_test
python .\evaluate_live.py --case textual_views --profile google_test --retrieval hybrid --embedding-profile google_embeddings
python .\evaluate_live.py --case recognition_chart --profile google_test
```

This runner has no demo option. It sends only the case question/scope, never its expected criteria. It records duration, execution status, answer artifact and a separate human-review record. Missing configuration is recorded as `execution_failed`, not a successful simulated benchmark. Exit 0 means execution completed, not that an independent reviewer found the answer correct; exit 2 requires revision.

Review SQL against independent source calculations, passage relevance, units, denominators, privacy and chart-question correspondence. Record unsupported/incorrect/refused cases as well. Compare the same cases and scopes across profiles; do not treat a small synthetic evaluation as production performance.

## Chart inspection

Accepted exports contain SVG graphics, exact selected CSV columns and JSON with source SQL/scope. Lime chooses the specification; the renderer never uses model-generated numbers. Check the visible title/axes, missing values, series and source/date footer against the CSV. SVG is a local artifact, not a frontend. ZeroSugar checks structured specifications; it does not see pixels. A general report/dashboard system is not implemented; `recognition_report.py` remains a separate fixed-report utility.

The classroom references and implementation mapping are in [REFERENCE_VALIDATION.md](REFERENCE_VALIDATION.md); role-specific examples are in [AGENT_ROLES.md](AGENT_ROLES.md).
