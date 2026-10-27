# Workflow reliability: current execution and repair contracts

## Corrected assertion review and phase-only retry: review-v5 (2026-10-27)

This supersedes v4's literal ordered reconstruction after all three live models failed
support review in runs 27-29. Original separates independently reviewable assertions and
their source subsets using the existing answer schema. ZeroSugar identifies each
substantive assertion in a short description (up to 600 characters), with kind, sources,
judgment and reason; it does not copy the answer/table/markup. Code assigns assessment
IDs within that review. Coverage of finding IDs and explicit assessments/references is
checked; semantic coverage, atomicity and entailment remain model judgments. Any failed
assertion still withholds its whole finding and creates a repair. Both review phases,
v3 correction judgments, source-facts replay and existing execution limits remain.

The CLI now captures complete private exchanges and per-phase checkpoints, excluding
credentials, with fresh-output/lineage checks. `--resume` performs only the failed phase;
review resumption cannot trigger Original/Vanilla or an automatic correction loop. A
completed completeness review is reused only with matching content and phase contract.
Other phase retries remain diagnostic, not a complete coordinator-process restoration.
See [the exact contract and limits](RESUME_AND_CAPTURE.md). No local tests/builds/live
calls were run by user instruction; earlier check totals predate this implementation.

## Assertion-level support review: review-v4 (2026-10-27)

User-selected option B supersedes whole-finding-only support submissions. Each finding
review now requires assertions with these fields:

| Field | Meaning |
| --- | --- |
| claim | Exact contiguous visible-finding excerpt, at most 12000 characters |
| kind | factual (including interpretations/premises) or proposal |
| citation_ids | Up to 16 unique known supporting references from that finding |
| assessment | supported, contradicted or insufficient_evidence |
| reason | Explicit explanation of support/limits, at most 300 characters |

Assertions follow visible-text order and cover the entire finding, with only whitespace
between excerpts. Keep headings/citations/punctuation with adjacent claims; a controlled
table can be assessed together. The model separates independently assessable statements,
including attributions, quantities, qualifiers and factual premises inside proposals.
Different assertions in a synthesis can use different source subsets. An assertion
attributed to every member of a group needs evidence for that full attribution. Novel
ideas and possible benefits are assessed as proposals, with their assumptions and
reasoning; their factual premises are assessed separately as factual assertions.

Code checks fields, literal ordered coverage, references, explicit assessments and the
1-64 assertion bound per finding. Supported factual assertions need citations when
evidence exists. No judgment is inferred, defaulted or silently sampled. Any contradicted
or insufficient_evidence assessment withholds its entire finding and forces revision,
even if the finding/global decisions say accept. Code creates one Original repair per
affected finding and retains all assessments for repair. Reviewers use corrections for
other problems, avoiding duplicate assertion repairs; Original may seek specialist help.

Literal coverage does not prove semantic atomicity or entailment. The model can still
combine claims incorrectly, misattribute support or misjudge a proposed action. The trace
makes those decisions inspectable, not guaranteed correct. No keyword, sentence-pattern
or case-specific classification rule is introduced.

New live reviews require assertions even with legacy administrative response fields.
Stored v2/v3 artifacts remain unchanged/readable without synthesized assessments. Legacy
correction-retention guards still apply on that input path, while new live results are
labeled review-v4. V3 keyed correction judgments continue inside review-v4. Five roles,
both phases, four drafts, source-facts replay, full sentiment input and all existing
provider/input/output/retry/shared-budget settings remain. Longer responses can exhaust
the unchanged output allowance; no mandatory model call was added.

Validated assessments are exported with findings and shown under Evidence checks in the
technical UI. Manager projections retain their existing fields. JSONL finding events
add counts only, not assertion text or evidence; minimized field diagnostics remain.
See [validation](TESTING_AND_RAG.md#assertion-level-support-review-2026-10-27) and the
[run 15-26 history](LIVE_TEST_HISTORY.md). No new live workflow has validated this update.

Reviewed 2026-10-26 against the current runtime and the audit follow-up. Earlier dated
sections retain their original change context; the current contracts below and the
[documentation map](DOCUMENTATION_MAP.md) identify the relevant implementation sources.

The five roles and final GW Azure default are retained. All manager-facing output is
English. This change does not add a UI, authentication system, bilingual testing or a
comparative provider benchmark. Later dated changes below supersede historical contract
details where explicitly stated.

## Reasoned actions and review simplification after run twenty-three (2026-10-27)

Original now requires all requested content plus at least one concrete manager action
reasoned from the analysis. The action may be a new idea absent from the prompt or source
text. Its factual premises are cited; its rationale, assumptions and possible benefits
are assessed as a proposal, not as observed outcomes. A justified validation step can
address insufficient evidence. Requested questions and actions serve different purposes.
Revisions preserve valid content and actions while allowing substantive corrections.

Completeness instructions are consolidated around visible user-request fulfillment.
Support distinguishes facts/interpretations from proposed action reasoning and evaluates
full sources rather than only illustrative excerpts. It retains explicit reassessment
of false/redundant objections without inferring semantic equivalence in code.

Original passes require_actionable=true to support review, recorded in support_contract.
The contextual corrections enum then permits policy_requirement; its validator requires
owner=Original and request_excerpt=null. User-requested omissions retain their exact
question-excerpt contract. Other review callers default to false and cannot introduce
this new correction kind. Existing routing/lifecycle handles a policy repair normally.
There is no new review phase or automatic prose/list-length test of action quality.
All source/privacy/arithmetic gates, four drafts, provider settings and budgets remain.
Saved runs are preserved; live semantic improvement is pending. See the
[validation record](TESTING_AND_RAG.md#reasoned-actions-and-review-simplification-after-run-twenty-three-2026-10-27).

## Requested content and additional actions after run twenty-two (2026-10-27)

Original's instructions prioritize all requested content and item counts while allowing
useful additional actions. Each action explains how it might address an identified
problem or sustain an observed strength from cited findings; proposed benefits are not
measured outcomes. Both completeness and support judge the function of visible content:
action recommendations alone do not satisfy requested team questions. An actual omission
requires correction even if supplementary content is useful. No punctuation, keyword or
fixed-layout gate infers that judgment. Support checks the action-to-finding connection
and proposed effects against evidence, without demanding extra actions for every task.

This instruction-only update preserves review-v3 reassessment and withdrawal of false
objections, both review phases, four drafts, existing source/privacy/arithmetic gates,
schemas, rubric, provider settings and budgets. Run twenty-two remains pre-change
evidence: the successful contract execution did not prevent accepting actions in place
of questions. Offline checks cannot establish improved live semantic judgment; see the
[validation record](TESTING_AND_RAG.md#requested-content-and-additional-actions-after-run-twenty-two-2026-10-27).

## Explicit correction judgments after run twenty-one (2026-10-27)

New live support tools use review-v3. Code preassigns every obligation as a required key
in correction_judgments. Each value contains mandatory (boolean), addressed (boolean)
and a reason of at most 300 characters. The model judges whether an independent repair is mandatory and
whether the current visible answer satisfies it. Optional/unjustified/redundant objections
may be judged not required; similarity of wording is never inferred by code. Evidence
off-screen cannot satisfy a requested visible deliverable.

The model does not submit lifecycle states or replacement IDs in this contract. Code
derives the existing exported correction_reviews shape:

| Explicit model judgment | Derived state |
| --- | --- |
| Not required | withdrawn |
| Required and not addressed | unresolved; preserve the original ID and repair |
| Required and addressed, inherited correction | resolved |
| Required and addressed, current completeness objection | withdrawn; the model judges its omission premise false in this same draft |

Full repair text is supplied once in review_obligations; the inherited list contains ID
references only and the completeness summary retains score/verdict/rationale/suggestions.
No obligation or source is dropped by this input compaction.

All keys, both boolean judgments and reasons are mandatory; missing/extra keys, non-boolean
values and invalid reasons are rejected without semantic defaults. Current omissions
remain blocking when judged required and not addressed, even if all findings are supported.
Judgments are preserved in the review artifact, and routing still derives from active
corrections. This simplifies administration, not semantic truth: model judgments remain
fallible and cannot override objective source/scope/privacy/arithmetic checks.

Legacy v2 state-list submissions remain readable through their existing coverage,
consolidation and current-omission retention checks, and are labeled review-v2. Stored
artifacts are not rewritten. The five roles, both reviews, source-facts versions, strict
transport, parallel-call restriction, full sentiment context and budgets are retained.
See [checks and live limits](TESTING_AND_RAG.md#explicit-correction-judgments-after-run-twenty-one-2026-10-27).

## Single-call review follow-up after run twenty (2026-10-27)

With one required tool, ChatModel requests parallel_tool_calls=false; other tool modes
are unchanged. Reviewers still reject multiple calls rather than silently choosing one.
Completeness rationale failures now expose types and bounded character counts, never
the rejected text. The saved run-twenty completeness phase completed in one live call
with a revise verdict; this is not full workflow or semantic-quality validation. See
[checks and evidence](TESTING_AND_RAG.md#single-call-review-follow-up-after-run-twenty-2026-10-27).

## Strict Chat transport follow-up (2026-10-27)

ChatModel preserves explicit strict tool flags at the Chat Completions boundary. The
APInex checks establish request acceptance and observed synthetic schema conformity;
they do not establish semantic correctness or constrained-decoding enforcement. Both
review phases and the existing correction retention/withdrawal protocol remain required.
Alternative B remains deferred. See [checks and limits](TESTING_AND_RAG.md#strict-chat-transport-follow-up-2026-10-27).

## Contextual support-review fields after run eighteen (2026-10-26)

Run eighteen completed after 27 successful calls, 530.453 seconds and four drafts.
The first three support phases exhausted their three attempts on invalid submissions;
the fourth candidate passed both phases. Source coverage, hashes, labels and aggregates
matched run seventeen. This demonstrates bounded recovery, not improved semantic quality.

The approved local follow-up builds the support tool schema per candidate. It includes
`numeric_reviews` only when trusted pending/error numeric requests exist, and
`correction_reviews` only when prior or current completeness obligations exist. Fields
that do not apply are omitted from both properties and required, then supplied as empty
lists in internal/exported results. A model-supplied inactive field is discarded; a
nonempty/invalid value produces metadata-only `unused_review_field_ignored` diagnostics.
This never supplies a verdict, closes an obligation or changes an active assessment.

Active fields retain exact ID/coverage/status/replacement validation. Required findings,
ratings, corrections, scope/source checks, both phases and shared budgets are unchanged.
Each call gets a copy of the baseline schema; reviewer reuse cannot retain an earlier
candidate's field exclusions. Repair feedback and schema identity use the actual tool
sent to the model. `support_contract` stores task counts only. Legacy review reading is
retained. No semantic rules, new agents or model changes were added. Tests were updated
and added but not run; no API calls, commit or GitHub push. Live effect remains unverified.

## General semantic guidance after run seventeen (2026-10-26)

The user approved simplifying instructions without reverting the earlier context and
traceability improvements. New reports use shared `survey-sentiment-v3`: general category
definitions and full-response contextual judgment with a brief justification. No rule
forces a label from the presence of praise, criticism or a particular closing phrase.
Case-specific guidance was removed from the active classifier, Original and ZeroSugar.
Historical v1/v2 definitions remain available under their original version identities.

This retains full released-group response/label input, privacy suppression, exact excerpt
checks, source replay, complete coverage, computed aggregates, request-grounded corrections,
independent reassessment, both review phases and the four-draft/shared-budget bounds.
No semantic keyword conditions, new roles, provider changes or new review stages were added.
Existing correction fixtures now supply literal request excerpts and expect their
retention; existing sentiment checks cover version identity and full canonical sources.
They were edited, not executed. No tests, model calls, commit or GitHub publication.
Run seventeen demonstrates the preceding version's operation, not this simplification's
quality. A later authorized run must preserve earlier artifacts and use a fresh filename.

## Sentiment and correction grounding after run sixteen (2026-10-26)

Implemented locally at the user's request, without tests, model calls, commit or GitHub
push. Run sixteen (`apinex_prueba_vanilla_16.json`, log
`20261026_205443_d0fc0454b26f.jsonl`) completed in 291.531 seconds with 15 successful
calls and two candidates. The final candidate passed both review phases. Read-only
source replay found 13 eligible comments, unchanged hashes, literal excerpts and matching
9 positive / 2 negative / 2 mixed counts. This is evidence for the preceding version.
The review introduced an invalid inference from full coverage to zero indeterminate
comments, described mixed as close to neutral, and demanded unrequested examples and
formatting. CMT27512 changed mixed to positive versus run fifteen on unchanged text.
Acceptance did not establish classifier accuracy or sound review judgment.

**Shared, versioned rubric.** `agents/sentiment_rubric.py` defines new
`survey-sentiment-v2` and retains v1 definitions. An explicit current criticism plus a
favorable evaluation is mixed even with a favorable overall verdict. Suggestions for
future improvement, continuation requests, initial doubt and resolved past issues alone
do not make a response mixed. Neutral and indeterminate remain distinct. Coverage does
not determine category counts. Vanilla stores the rubric version and includes it in
the progress-reuse key. Reports without the field replay as v1; historical artifacts and
source-facts-v4/v1-v3 are unchanged.

**Grounded corrections.** New completeness corrections include issue, requested_change
and an exact nonempty request_excerpt of at most 400 characters. New support corrections
also declare request_excerpt (nullable for factual or usability problems); new
missing_deliverable entries require a non-null excerpt. Code checks literalness and
retains the supplied fragment instead of discarding it. Model judgment must still explain
why that question fragment requires the repair. A factual correction names the claim
and conflicting evidence. Original challenges unjustified or contradictory repairs;
ZeroSugar independently withdraws or reassesses them through the existing obligation
lifecycle. Valid citation IDs and explicit denominators do not mandate clickable links,
fractions, examples for every category, or repeated numbers. Legacy review submissions
remain readable; the original question remains authoritative without a deliverable checklist.

**Full semantic-review input.** The sentiment tool attaches canonical response passages
for every classified comment in a released team/date/dimension group. Summary examples
remain selected illustrations. Support receives `sentiment_classifications`: trusted full
response text, label, literal excerpt, reason and the report's versioned rubric for all
released groups. Source hashes, scope, aggregation and the existing five-comment privacy
threshold are checked first. Suppressed groups' texts are excluded. Coverage diagnostics
contain rubric versions and eligible/included/suppressed counts only, not response text
or question excerpts. The existing 150,000-character review-input bound is unchanged;
oversize input fails review rather than silently sampling. Both phases and all shared
budgets remain required. Model review is not human validation; labels remain provisional.

No new role, provider change, budget increase, wording-pattern rejection or automatic
sentiment relabeling is introduced. A disputed label still requires Vanilla's analysis
and a new accepted review; unresolved disagreement cannot certify the classification.
Tests and a fresh live evaluation of this update remain unrun. Preserve run sixteen.

## Review recovery after run fifteen (2026-10-26)

This local update supersedes the earlier diagnostic-only behavior below. No GitHub
publication or new live call is part of it. The repeated run fifteen reached both
review phases: completeness repaired object-valued suggestions, then support omitted
clarification_question, omitted suggestions, and finally attempted to resolve a current
completeness correction without changing the draft. The new diagnostics exposed these
conditions; additional retry budget was not the missing resource.

**Transport versus judgment.** The canonical review-v2 tool shape is retained. At the
input boundary only optional annotations receive neutral normalization: omitted
suggestions become [], malformed optional suggestions are omitted as a whole, and an
omitted support clarification_question becomes null. Normalization is explicitly traced,
without rejected values. A clarify-owned correction still requires a real question.
No verdict, rating, finding review, correction, obligation assessment, numeric decision,
source check or evidence is synthesized, repaired by coercion, or silently dropped.
Missing essential fields and unknown fields retain bounded structural retries.

**Obligation lifecycle.** An attempted resolved status on a current completeness
correction is retained as unresolved, rather than invalidating the entire support
submission. Diagnostics identify the candidate, correction ID, index, model attempt,
submitted/effective statuses and the application reason. The original model reason
remains in the assessment, separately from the application adjustment metadata.
This can only preserve mandatory repair; it cannot grant approval. False omissions
may be withdrawn with a reason identifying content already visible in the draft,
as may unjustified requirements/policy conflicts. Source material attached outside
the answer still cannot satisfy a requested visible example. Prior corrections,
complete assessment coverage and consolidation safeguards remain in force.

**Progress without premature release.** If all three support submissions are invalid
but completeness produced validated corrections, ZeroSugar raises ReviewRepairNeeded
with pending obligations and candidate identity, not a VerificationResult. Within
Original's four-draft limit (initial answer plus at most three revisions), the coordinator
may reuse evidence and prepare another draft while a round remains. Both reviews must
then finish normally before acceptance. Failed
support is not counted as a completed review, no candidate becomes reviewed through
this path, and no findings/charts are released from it. Recovery is available after the
first, second and third drafts, with no fifth draft. Missing usable corrections, provider
failure or an exhausted shared budget does not manufacture approval or extra rounds.
Metadata records review_repair_requested with draft number and draft limit. ZeroSugar
still has three structured-submission attempts per phase per draft. Shared model-call,
tool, time and output-token budgets are unchanged; success stops the loop immediately.

**Context and consistency.** Completeness now receives trusted manager/date scope
and, when available, the authorized team names retained from ScopedData by Cherry or
Vanilla (or obtained by standalone ZeroSugar). It still receives no source evidence,
SQL, specialist answer or checklist. Instructions require reading all visible tables
and distinguishing contradictions from omissions. Original/Vanilla distinguish selected
examples from category totals and show requested examples through literal quote fields.
Semantic review remains fallible; these instructions are not keyword-based validators.

Five roles, source-facts-v4/v1-v3 replay, provider settings, classifier rubric, shared
budgets, scope/quote/coverage/arithmetic/privacy gates and reviewed-version release remain.
The Chat adapter's strict-flag handling and provider support have not been changed or
probed. See [validation](TESTING_AND_RAG.md#review-recovery-checks-2026-10-26).

## Field-error diagnostics follow-up (2026-10-26)

After run fourteen, the user authorized a diagnostic-only update. Object-field errors
now identify expected/received root types, allowed/received fields, missing required
fields and additional fields, with an indexed path for nested items. New review roots
and correction items are checked against the actual tool schema, not a duplicate root
field list. Legacy review acceptance/compatibility is retained, with explicit diagnostics
for its supported shapes. This does not relax field validation or guess default values.

The same bounded/redacted field-name metadata survives error summaries, JSON artifacts,
JSONL and model repair feedback. Up to 64 names of 160 characters are retained per list;
counts/truncation metadata disclose limits. Unrecognized non-identifier keys are replaced
with stable redacted-field markers so a key cannot copy source prose into the trace.
Rejected values, complete arguments, prompts
and source text are not added. The previous missing-field filter limited to grounded
answer slots has been replaced. Feedback identifies fields to add/remove and preserves
valid values, rather than merely repeating the schema instruction.

Each rejection includes candidate/phase/attempt context, review version, the declared
tool-schema fingerprint and a stable diagnostic condition ID. The validated object's
schema fingerprint may differ for a nested or legacy shape. Retry state distinguishes
first_failure, repeated and changed; a changed condition is not proof of a valid review.
The existing three-attempt bounds remain. Final valid submission updates diagnostic
resolution and emits structured_response_repaired events linked to the original rejected
attempts. That event confirms structured submission repair, not factual/semantic approval.
Both review stages and all publication gates remain required.

No completion-scope/source-review rules, role responsibilities, provider strict-mode
handling, model settings, budgets, source contracts or UI layouts are changed here.
The incorrect completeness objections in run fourteen and provider-schema compatibility
remain separate follow-up work. Old logs cannot retrospectively reveal missing keys
that they never recorded. See [TESTING_AND_RAG.md](TESTING_AND_RAG.md) for validation.

## Review and data contract update (2026-10-26)

Implemented after examining live runs twelve and thirteen. Those runs remain unchanged
local evidence; this update is not a claim of improved live-model behavior.

**Data and roles.** Echo analyzes supplied data by definitions, coverage and method,
without presuming or warning that it is synthetic. Supplied assumptions remain inputs,
not measured outcomes. Causal support depends on evidence/design. Model-label uncertainty,
source integrity, anonymity, scope and denominator controls remain. Dataset-construction
history stays in dataset documentation. The five roles and provider settings are retained.
Original's internal analysis plan selects queries/specialists. Its manager-facing action
plan proposes useful responses to findings when requested or useful, without mandatory
per-question templates, invented targets, schedules or resources. No action is executed.

**Single-list review.** New `review-v2` support submissions contain `corrections`, not
parallel `issues` or `repair_targets`. Each new correction has issue, kind, owner,
requested_change and citation_ids; code assigns IDs and derives compatibility fields.
At that update, new completeness submissions contained issue/requested_change corrections plus their
verdict/rationale/suggestions. They see the exact visible answer and safe chart labels,
never attached sources. Original owns visible-answer repairs with available evidence.
Legacy review submissions remain readable through conservative normalization.

**Independent reconsideration.** Support receives prior corrections and current visible
corrections as `review_obligations`. Every ID requires an assessment: resolved,
unresolved, withdrawn with reason, or consolidated into another unresolved obligation.
Consolidation cannot cycle or point to a closed obligation. Existing unresolved IDs
persist; code does not infer semantic equivalence from wording. Current visible omissions
cannot be marked resolved merely by source acceptance. A withdrawal must explain an
unjustified requirement or policy conflict. Original may challenge a correction, but
ZeroSugar decides its disposition; objective source/scope checks remain non-overridable.
Optional suggestions never create required repairs. Ratings/blocking decisions must have
an actionable correction or an objective/finding failure; the existing publication
thresholds remain. Both review stages must succeed before a complete release.

**Plan relevance and autonomy.** Each pending numeric task gets a code-assigned request
ID. ZeroSugar returns required/not_required/uncertain plus a reason against the question.
Required and uncertain tasks stay open; a not-required catalog task is retired from the
remaining internal plan. This judgment shares the existing support call. The original
question also governs comparisons omitted by the plan. Correction owners determine
repair targets; Original may use either analytical specialist when resolving integration
work, subject to role/scope controls and retained-evidence reuse. Formatting an available
excerpt does not require reclassification. No extra agent, ordinary review call, budget
increase or natural-language rejection rule is added.

**Diagnostics and release.** Structural repairs identify the failing type, index, count
or length without storing rejected prose. Valid review fields are retained. Each completed
phase is immediately saved locally with bounded/redacted review text; JSONL phase events
contain metadata only. Finding events are provisional until the entire review validates.
Original preserves per-candidate phase history, including a completed first phase if
support fails. Candidate fingerprints include answer, evidence and charts. A partial
artifact records the reviewed source candidate, released finding IDs, latest candidate
ID and a separate unreviewed draft when applicable. Published claims/evidence come from
the reviewed version, never a newer unreviewed draft; the partial wrapper is not itself
a full grounded selection. `audit_grounding.py` replays the source candidate and checks
the released selection. UI payloads expose only review status/counts/IDs, not retained
drafts or review traces; completed-review counts differ from attempted draft counts.

**Replay/export.** New answers use `source-facts-v4`, removing automatic origin claims.
Stored v1/v2/v3 keep their original rendering; v3 narrative warnings remain warnings.
SVG descriptions and new provenance exports no longer assert `synthetic=True`. Existing
artifacts/exports and source records are not rewritten. See [SOURCE_GROUNDING.md](SOURCE_GROUNDING.md)
and [TESTING_AND_RAG.md](TESTING_AND_RAG.md) for compatibility and validation boundaries.

## Audit follow-up: review coverage, output limits and request deadlines (2026-10-26)

The later [review/data contract update](#review-and-data-contract-update-2026-10-26)
supersedes the review formats and automatic pending-metric blocking described in the
earlier sections. Provider deadline/output-limit changes remain in effect.

ZeroSugar must assess every prior correction, even when its response omits the entire
`correction_reviews` field. Missing, empty or partial assessments fail validation when
corrections are pending. Legacy reviews without prior corrections remain readable.
Python checks coverage; ZeroSugar still judges whether Original resolved each issue.

Responses profiles now pass `max_output_tokens` from `connections.json` through
`ModelRegistry` to the request and usage diagnostics. The fallback remains 3500;
existing configured limits and the Chat adapter's token handling are unchanged.

All six budgeted generation call paths use `RunBudget.respond` to scope the existing
deadline to one model call, including its retries. The shared client retains no workflow
deadline. Chat checks this deadline before each adapter-controlled attempt and after
pacing waits, before incrementing actual request counters or sending HTTP. Expiry uses
the existing time-limit failure path. Waiting and in-flight requests are not cancelled;
SDK-internal retries keep their existing settings. Unbudgeted connection probes retain
their existing behavior. No role, UI, source contract or provider setting changes.

Focused offline validation and its limits are recorded in [TESTING_AND_RAG.md](TESTING_AND_RAG.md).

## Autonomous synthesis and two-stage review (2026-10-23)

The user selected options 1A, 2A, 3A, 4A, 5B, 6A, 7B and 8A after reviewing run eleven.
Original's overlapping instructions are consolidated around role ownership and complete,
useful answers. It uses adequate specialist analysis as the basis for integration and
preserves supported meaning, differences and limits without freezing wording. Vanilla
retains textual interpretation, the existing answer/evidence format and standalone use.
The mandatory per-question deliverable checklist is retired from planning, delegation and
review. Old plans carrying that field remain readable; it is ignored. Only corrections
arising from an actual review are retained between candidate versions.

ZeroSugar performs two sequential calls, with separate histories, for every candidate:

1. `submit_completeness_review` sees the original question and exact visible answer,
   with titles/axis labels/units for accompanying charts when present. These descriptions
   contain no source IDs, SQL, rows or provenance.
   It judges task coverage, allowing useful presentation and explanations of unavailable
   evidence. It has no attached sources, specialist prose or predefined checklist.
2. `submit_review` receives the answer, scoped evidence, claims, chart plan, objective
   checks, the completeness verdict and any prior corrections. It checks support and
   interpretation, including disagreement and context across sources, and reviews prior
   pending items against the complete revised package.

An omission identified in the first stage remains an issue even when its content exists
in attached evidence or the support reviewer accepts. The combined Completeness score
cannot exceed either stage's score. Optional suggestions do not force revision. Supported
blocks may still be released as partial output under the existing scope/safety gates.
Each phase has up to three structured-response attempts within the same shared model,
tool and elapsed-time budget; failures never constitute approval. This historical update
retained two candidates; the current run-fifteen recovery contract above allows four.
A normally valid review adds one model call per
candidate compared with the former single-stage path. Latency, cost and live analytical
improvement remain unmeasured for this update.

New source-review findings return `finding_id`, `decision` and `reason`. Code attaches the
unchanged citation IDs from the candidate block. The reviewer still judges whether those
sources support the meaning. Legacy findings that echo citations remain readable and are
checked for a match when supplied. Unknown, repeated or missing finding IDs remain errors.
New corrections need no literal copy of the user question; legacy correction excerpts are
accepted for compatibility but not retained in new correction metadata.

`diagnostics.review_phases` and phase log events retain only phase, status, attempt count,
decision and issue count. They do not duplicate questions or source text. Actual issue,
correction and finding-review records remain in the ignored local artifact; existing
bounded/redacted narrative diagnostics are unchanged. Reports and logs are not published.
The UI's answer/status/findings interface is retained; backend manager-view allowlists do
not expose the new technical diagnostics.

Sentiment classification, literal-excerpt validation/repair and routing flags are retained.
No model/provider change, new agent, SQL permission, identity field or chart control is added.
The source-facts-v3 answer contract and historical v1/v2 replay remain in place.

Validation: the initial 223-test suite had 15 failures and 4 errors before edits. Historical
v2/normalization assertions and fixtures were aligned with their declared contracts instead
of restoring superseded restrictions in v3; a partial-result compatibility defect was fixed.
The final agent suite passed 242 offline tests on Windows Python 3.12.14, including 19 new
phase-isolation, release, citation, privacy, budget and repair regressions. Tests use
scripted/mocked judgments; no live generation/embedding provider request was performed.
GitHub publication is authorized after validation. A fresh live run remains necessary to
assess actual model behavior; preserve run eleven and use a new artifact filename.

## Requested deliverables and explicit corrections (2026-10-22)

Historical: the mandatory checklist below was retired by the 2026-10-23 update above.

The tenth live run reached two completed reviews and released six supported blocks as
`partial`: requested positive/critical literal examples were present in the evidence but
absent from both candidate answers. This first-stage update preserves specialist formats,
standalone use, source-facts-v3 and all five roles. Evidence-only handoff remains deferred.

Original's existing planning call requests up to 16 `deliverables`: an exact
`request_excerpt` (up to 400 characters) and analytical `owner`. Python assigns `D1`, `D2`,
etc. and checks structure, roles and literal request provenance, not task meaning or full
coverage. The original question remains authoritative. The same checklist reaches Original,
the assigned specialist and ZeroSugar. Original owns the complete visible answer; attached
examples are evidence, not proof that the answer displays requested examples. Old plans
without the field remain readable as an empty checklist with full-question review.

ZeroSugar's review call requests one `corrections` entry per mandatory `issues` item:
zero-based `issue_index`, `kind` (`unsupported_claim`, `missing_deliverable` or
`unusable_presentation`), `owner`, `requested_change`, available `citation_ids`, and an exact
`request_excerpt` or null. Code assigns `C1`, `C2`, etc. within that review. Source references,
field bounds and issue coverage are structural checks, not semantic verdicts. Presentation
omissions with evidence available belong to Original; missing/disputed analysis can require
Cherry or Vanilla. Optional wording preferences belong in suggestions. An intelligible
question introduced by "Ask the team:" is still a question. Examples are required when
requested, not for every classification or interpretation.

The correction pass receives all pending entries and retained evidence. The next review
returns `correction_reviews` (`correction_id`, `resolved`/`unresolved`, reason) for every
previous item and checks the complete revised package. A model-assessed unresolved item
remains an issue even if omitted from the new issue list; a resolved flag never bypasses
source checks, finding review or acceptance gates. No prose-pattern rule decides semantic
completion. Legacy reviews retain their issues/targets without invented links or assessments.
Runtime coverage/chart failures also retain concrete corrections. Partial output names
current reviewed gaps with bounded redaction instead of inferring them from agent names.

No mandatory model call is added. Two candidate versions, classification attempt limits,
time/call/token budgets, privacy/scope gates and chart controls remain in place. Prompt and
response size grows; cost or quality gains are unmeasured. No tests, artifact replay,
provider calls or GitHub publication were performed at the initial implementation stage,
by user instruction. The user later authorized publication; that follow-up does not
establish runtime or analytical quality (see PROJECT_CONTEXT.md).

## Narrative review signals and presentation v3 (2026-10-21)

The ninth live run completed 13 classifications but exhausted Vanilla's and Original's
seven turns on final-answer validation. Nine rejections detected narrative digits; the
other three rejected inline citations, a non-text aggregate source, and a null quote.
It made 17 successful provider calls in 328.235 seconds and never reached ZeroSugar.
These counts explain the failure path, not semantic label quality.

The first-stage correction uses `source-facts-v3`. Narrative quantities and quantifiers
in interpretations/proposals now attach `review_warnings` rather than raise validation
errors. The markers describe a review focus, not proof of false meaning. They never enter
`deterministic_issues` and do not by themselves force rejection or an extra model call.
ZeroSugar receives each flagged phrase, references and trigger, with available code-computed
comparisons (at most 64, selected facts prioritized, omitted count explicit). Its existing
per-finding reason must explain support/uncertainty, units, denominator, period, population
and proposed-versus-observed status where relevant. The model does not need to recreate
inequality chains. The same configured verifier can still make semantic errors.

V3 interprets text or source rows through one or several cited sources with `quote=null`.
An explicitly supplied example quote remains exact and bounded at 400 characters; the
reviewer checks whether the requested positive/critical examples and interpretation are
actually present. Whitespace/newlines and known citation wrappers/inline IDs normalize
without another model turn. Unknown structured source IDs remain errors; ordinary prose
brackets are escaped rather than misread as citations. Each narrative item is one review
unit. Controlled numeric facts, source/scope integrity, anonymity, classification coverage
and exact source matching retain their objective checks. Stored v1/v2 answers retain their
original renderer behavior instead of inheriting v3's relaxed presentation.

Local JSON/JSONL rejection records now include bounded redacted context for the indicated
narrative item and correction feedback. `answer_normalizations` records received and
normalized presentation; `review_warnings` records signals and the verifier's eventual
per-finding assessment. Known credential/email/employee-ID/SSN/phone patterns are redacted;
unknown fields and full prompts/provider payloads are omitted. Pattern-based redaction
does not detect every personal detail, so these diagnostics remain local. Source-answer
context is an explicit exception to the older minimized-only diagnostic contract below.

No tests, saved-artifact replay or API calls were run for this update, as requested.
Static source/syntax/diff review does not establish successful live behavior. The next
local attempt should preserve run nine and use `reports/apinex_prueba_vanilla_10.json`.
Success requires the requested cited answer and a completed independent review; changing
the status label or bypassing review is not success. Five roles, provider settings,
turn/call/time budgets and tools are unchanged. Specialist evidence-only handoff remains
a separate second-stage proposal, not part of this implementation.

## 3. Validated recurring metrics and exploratory SQL

Cherry has `run_metric(metric, dimension)` alongside `describe_schema` and `execute_sql`.
Original's live plan lists all required catalog metrics, including one request per survey
dimension in a comparison. The application prepares these metrics before Cherry interprets
them. Cherry retains `run_metric`, `describe_schema` and `execute_sql` to complete missing
or custom calculations. Identical metric arguments reuse the original result/citation ID
within the workflow. Single-metric selection no longer disables Cherry's tools.
The catalog runs read-only SQL on the physically scoped in-memory copy:

| Metric | Definition |
| --- | --- |
| `cross_team_contributions` | Distinct cross-team Contribution_ID; separate counts with/without manager recognition, with partner feedback, and without any feedback. `dimension=null`. |
| `survey_trend` | Recorded team/date aggregates for one exact dimension, preserving response denominators. |

Distinct IDs and EXISTS prevent feedback joins from multiplying contributions. Dimensions
use bound parameters. Empty populations return zero counts. Feedback is restricted to the
selected interaction period; missing notes do not prove absent recognition or unfairness.
`survey_trend` version 2 matches complete dimension names without case sensitivity and
strips surrounding input whitespace; it does not use fuzzy matching. Empty survey results
mean no matching publishable rows, not zero scores or proof of a backend error. Prepared
metric rows and citation IDs are included in Cherry's model history before interpretation.
Original validates a planned survey dimension against the authorized copy's schema metadata
and requests a corrected plan for an unknown topic such as `quarter` before executing it.
Metric artifacts include version, definition, arguments, SQL and parameters. ZeroSugar
replays both SQL and metric definition. Custom SQL remains available. A conservative guard
rejects the known contribution/feedback JOIN + COUNT(*) mistake; it does not prove the
semantics of every generated query.

Code-generated `numeric_coverage` records each planned request as `pending`, `error`,
`no_rows` or `with_results`, with its citation ID where available. Original uses these
states to coordinate pending work without recalculating metrics; ZeroSugar receives them
for independent review. Unqueried data is not absent data. The model must still map the
original question to the right plan, and ZeroSugar must check for omissions in that plan.

## 4. Bounded closure and reuse

The shared specialist loop allows at most seven model turns. In live source-grounded
Original/Cherry/Vanilla runs, the closing turn retains the response tool
`submit_grounded_answer`; Cherry/Vanilla can also submit `decline_task`. Data/delegation
tools close at the bound. The legacy/scripted path can ask for free-form closure without
data tools; this is not the live factual-answer contract.
Each turn states the remaining allowance. Identical tool requests reuse their result within
that run and trigger closure only when no planned Cherry metrics remain unresolved.
Hard turn/tool/time limits still force bounded closure with explicit limitations. A failed or
noncompliant model produces an explicit failure instead of invented conclusions.

## 5. Selective roles

Original submits a typed plan: numeric evidence, text evidence, optional chart or a
necessary task clarification. Full comment sentiment has its own `needs_sentiment` flag;
its counts/percentages require Vanilla, not SQL/rating metrics. Planned/repair-target
specialists are available, with corrected routing enabled after an out-of-role decline.
Simple SQL counts can skip Vanilla and Lime. Analytical findings still require ZeroSugar review. Clarification
responses contain no analytical findings.

## 6. Localized repairs

ZeroSugar selects repair targets: Cherry, Vanilla, Lime, Original or clarification. The
single correction pass permits only affected specialists. Chart-only repairs reuse the
candidate and calculations. Unchanged chart plans are reused when another role is repaired.
Sources and the final package are still reviewed. Tool/classification progress is not
reused across independent workflows. Optional persistent embedding caches are separate
and scoped to source/provider/model identity, as described in TESTING_AND_RAG.md.
Preserve supported facts, meaning and provenance during repair, rather than freezing
their previous wording or block layout. Original may reorganize, synthesize cited text
and remove redundant presentation. The revised candidate is independently reviewed again.

## 7. Review by finding

For current live Original/Cherry/Vanilla runs, [SOURCE_GROUNDING.md](SOURCE_GROUNDING.md)
supersedes paragraph splitting: `submit_grounded_answer` selects reproducible facts and
returns explicit individual claims, with tables and their source citations kept together.
ZeroSugar receives those claims directly; Python independently rebuilds their numeric
content before accepting any model verdict. The paragraph path below remains for older
artifacts and scripted fixtures, not a guarantee of semantic correctness.

Each substantive paragraph/block, including uncited blocks, receives an independent
review with its original ID and citation IDs. When evidence is available, uncited blocks
are withheld until explicitly grounded. Plain headings and standalone Markdown separators
(`---`, `***`, `___`) are excluded. Blocks containing substantive text remain reviewable,
including uncited claims. All claims in a block must be supported; one unsupported claim withholds that block.
The reviewer cannot rewrite the text into a new claim. IDs refer to the candidate currently
being reviewed, not a frozen layout across revisions. Missing/repeated findings or changed
source IDs invalidate the review. Source checks also run per block. A safety failure or
deterministic package error prevents partial release. English is the application policy.

`supported` means the finding passed implemented source checks and independent model
review, not human validation or measured semantic accuracy. Units are text blocks, not a
guaranteed atomic-claim parser. Legacy four-field reviews are allowed only in offline
fixtures; live reviews require finding coverage and repair targets.

## 8. Informative outcomes

| Original status | Released content | Exit |
| --- | --- | --- |
| `complete` | Accepted answer and findings | 0 |
| `partial` | Independently supported blocks plus unresolved work | 2 |
| `needs_clarification` | Necessary task question; eligible reviewed blocks only | 2 |
| `failed` | Explanation and next step; no unverified conclusions | 1 |

Artifacts include `findings`, `limitations`, `next_steps`, `clarification_questions` and
safe `failure` metadata. Rejected drafts and withheld blocks stay local for diagnostics;
a future UI must not render them as approved findings. Direct specialist results remain
`unverified` until reviewed. Incomplete survey classification still produces no partial
sentiment percentages. A standalone specialist may instead return `declined` or
`incomplete` (exit 2), with a structured task outcome; neither is verified analysis.
Charts are withheld for incomplete packages. Known failures also
write an explicitly failed artifact when `--output` is supplied; successful artifacts are
saved before printing. Cancellation remains exit 130 with an incremental execution log.

### Shared rules and initial planning clarifications (2026-10-21)

[policies.py](agents/policies.py) contains six short instruction rules: evidence,
uncertainty, authorized scope, clarification, untrusted content and execution limits.
The existing runtime composes them with Original/Cherry/Vanilla role instructions;
Original's separate planning call, Vanilla's sentiment batches, ZeroSugar and Lime
compose the same rules directly. Connection probes remain minimal diagnostic calls.
General duplicate instructions were removed; role-specific tools, privacy restrictions,
source checks, source-bound rendering and independent verification stay in their modules.
This is prompt/configuration engineering, not model training or a new policy agent.

Initial plans now require nullable `clarification_basis` alongside
`clarification_question`. A proposed question identifies a missing field/detail, its
blocking reason and an exact excerpt from the original request. Code rejects invented
excerpts, incomplete justification and requests for already supplied scope fields.
Before showing an otherwise valid planning clarification, Original must reconsider the
complete original question and scope in its existing two-attempt planning loop. It can
remove the question and continue, or confirm a necessary ambiguity. A plan without a
clarification needs no extra call. Exhausted retries/budgets fail explicitly; the system
does not assume a missing answer or repeatedly question the user. The two attempts are
shared with schema repair; a late clarification has no additional retry allowance.

These observable checks are not a general semantic detector: a literal excerpt and
plausible justification can still misinterpret the request. Reconsideration uses the
same model, not an independent reviewer. Review-driven clarification retains the existing
ZeroSugar/Original release gates and now receives the common instructions too.
Delegated Cherry/Vanilla tasks include the full original request as context while keeping
their bounded specialist task and fixed access scope. Resolved information is reused only
within supplied context; there is no persisted conversation between terminal invocations.

Planning diagnostics now retain bounded, redacted clarification fields for rejected or
normalized plans; see the planning update below. The optional ignored JSON artifact also
records the accepted clarification basis. Historical regression
checks in [test_clarification_policy.py](tests/test_clarification_policy.py) exercise these
paths using scripted responses, not provider reasoning. The user's third APInex run
(`reports/apinex_prueba_media_3.json`) stopped after one planning call with an unnecessary
clarification. The fourth run subsequently planned and completed without clarification;
that does not exercise reconsideration of a new unnecessary question. Interactive
terminal continuation, natural-language date resolution and authenticated manager selection
remain deferred; `run_agent.py`, connections and request pacing are unchanged.

### Planning normalization and diagnostics (2026-10-21)

When Original proposes no clarification question (including the existing empty/null-like
string normalization), an unused non-null `clarification_basis` is set to null rather
than rejecting the plan. All other plan checks remain in force. A real clarification
still requires a valid basis and reconsideration within the same two planning attempts.

Rejected and normalized attempts are written to the incremental JSONL log and to
`diagnostics.planning_attempts` in the result, including on planning failure. Each record
identifies the attempt, status, validation cause, received clarification values, correction
feedback and `feedback_retry_available`. That flag means another planning attempt remains,
not proof of successful provider receipt. A normalization does not consume another call.
The last rejected attempt records feedback with no further retry available.

Only the two clarification fields and the four declared basis fields are retained, with
value types and bounded strings. Recognizable credential patterns, email addresses,
employee IDs, US Social Security numbers and phone numbers are redacted. Unknown object
fields and malformed list contents are omitted with structural metadata; full prompts,
provider payloads and source records are not added. Pattern redaction cannot detect every
form of personal information; these remain local diagnostic artifacts.

Run eight (`reports/apinex_prueba_vanilla_8.json`,
`logs/20261021_171341_9c0e36b4cea2.jsonl`) failed in planning after
`unexpected_clarification_basis` followed by `clarification_basis_required`, with two
successful provider calls and no specialist/reviewer execution. These changes follow that
observation. Per user instruction, no tests or provider calls were run for this update;
existing test results predate it. The historical strict orphan-basis regression describes
the former behavior. Roles, scope, other validation rules, budgets and provider settings
are unchanged; live confirmation is pending.

## 9. Diagnostics

Automatic local JSONL logs include plan choices, skipped roles, remaining budgets,
closure, request fingerprints, cache hits, metric execution/replay, finding decisions,
repair targets and final response status. They exclude raw queries, prompts, answers,
employee records, credentials and provider payloads. Optional local artifacts retain the
detailed evidence; legacy narrative paths may also retain `diagnostics.last_unverified_text`.
Live source-bound answer failures use bounded records. The current v3 exception above
adds redacted narrative context and feedback; the dated minimized-only design below is history.
Diagnostic content is never a released finding. Known citation wrappers are normalized without
creating new source records. Provider null sentinels are handled as absent values, not questions. All reports/logs remain ignored by Git.

Structured validation errors additionally record a stable validation code, field path,
record index and known source/finding ID where applicable. Literal quote mismatch and
quote length are separate failures. Reviews report missing rubric dimensions, finding
coverage, invalid fields and changed citations through separate codes. No rejected quote
text or arbitrary provider exception is written to the execution log.

### Rejected source-answer diagnostics (2026-10-21)

`diagnostics.rejected_attempts` retains source-bound answer validation failures and
free-form answer attempts in the ignored local JSON artifact, including after success
or exhaustion. Each entry identifies agent, tool, model turn, rejection index, field,
element index when relevant, stable code and a fixed application explanation. Type,
count and unknown-ID errors are distinct, as are quote type, length and literal mismatch.
At that diagnostic-only revision the acceptance predicates were unchanged. The later
[repair and recovery update](#repair-feedback-and-retained-evidence-2026-10-21) permits
quarter/ISO-date references; analytic quantities and prevalence claims still require facts.

The new diagnostic deliberately omits full arguments, rejected prose, source quotes,
names, contact details and credentials. It keeps only types/counts/positions and
allowlisted fragments: a fixed-format `FACT_` hash, a Q1-Q4 marker, or the exact
quantifier keyword. Other content is omitted rather than relying on incomplete PII
pattern redaction. Thus it explains the condition without recreating the entire rejected
statement. General JSONL logs retain only an explicit metadata allowlist, never these
fragments or explanations. Existing evidence artifacts still contain authorized source
data; this change does not anonymize an entire report.

Entries remain `rejected_unverified`; `resolution=accepted_source_submission` and
`accepted_model_turn` indicate a later locally valid submission, not semantic approval.
The accepted payload remains separately in `grounding.payload` and goes through ZeroSugar.
Original's history survives its independent-review repair rounds; each child's history
is retained in that child's delegation artifact. New workflows reset their history.
Retention is capped at 16 entries per agent history, with `rejected_attempts_omitted`
counting excess entries. No diagnostic content is added to released claims or the normal
terminal answer. Planning/reviewer/batch and ordinary tool diagnostics keep their existing
contracts; this update specifically fills the source-answer rejection gap.

The fourth live run predates this feature, so its missing rejected payloads cannot be
recovered. Tests use controlled sensitive-looking strings to check omission, success and
failure persistence, repair-round continuity and unchanged call counts. An offline replay
also reproduced the fourth run's accepted answer and claims exactly. No API calls were
made for this diagnostic update; roles, tools, budgets, connections and pacing are unchanged.

Vanilla permits exact contiguous quote excerpts of 1-400 characters; 400 is a maximum,
not a requested length. Explanations remain capped at 160 characters. Classification uses
20-comment batches and at most three attempts per batch. Valid records are retained while
only unresolved comments and bounded error reasons are sent in a fresh repair request.
No partial sentiment percentages are produced. Local schema/quote checks establish
provenance and completeness, not semantic label accuracy.

Behavioral tests cover duplicates, parameter binding, closure, reuse, role selection,
localized correction, finding coverage and safe partial release. These implementation
checks do not replace the deferred comparative live evaluation.

## Sentiment routing, retained progress and task declines (2026-10-21)

The fifth Luna run failed before ZeroSugar: the plan confused comment-label percentages
with SQL ratings, repeated Vanilla delegations restarted classification, and individual
comment IDs were unavailable as text evidence for the final claim contract. The repair
keeps the five existing roles and their source checks; it adds no preflight agent or
mandatory model call.

- Original's plan marks full comment classification with `needs_sentiment=true` and
  `needs_text=true`. This does not imply `needs_numbers` or survey-rating metrics.
  Counts/percentages derived from labels stay with Vanilla; separate SQL requests stay
  with Cherry. The model must still correctly interpret the user's question.
- Cherry, Vanilla and Lime can submit `decline_task` alone, in an existing turn, with
  a bounded explanation and `out_of_role`, `missing_input` or `insufficient_evidence`.
  Original receives the structured outcome and can correct the recipient/task. Identical
  declined or incomplete requests return their existing outcome without another child
  call; an out-of-role decline enables corrected specialist routing. Optional no-chart
  completion remains distinct. Standalone CLI declines/incomplete results exit with 2;
  these outcomes do not masquerade as successful analysis or absent data.
- Vanilla retains valid records and per-batch attempt counters across delegations in
  one workflow. Input identity includes scope, source content, model instance/name,
  mode, dimension and rubric version. Only pending comments consume up to three total
  classification attempts per batch; a provider interruption also consumes an attempt.
  No cross-workflow cache or automatic budget increase is introduced. Exhaustion returns
  `incomplete` with eligible/validated counts and pending IDs, without percentage rows.
- A quote copies contiguous response text verbatim, including punctuation and relevant
  negation, with a 400-character maximum. Summaries/explanations belong in `reason`, not
  `quote`. Publishable summary examples expose canonical individual text evidence so
  Vanilla and Original can submit valid source-linked interpretations. ZeroSugar checks
  those records against trusted scoped responses as well as recomputing the full summary.
- ZeroSugar receives task outcomes and the required-classification flag, retained for
  standalone artifact review. Requested classification without complete evidence cannot
  receive final acceptance. This is a coverage failure, allowing unrelated independently
  supported findings to remain partial; an actual integrity/safety failure still blocks
  partial release. Prior failed attempts do not invalidate a later complete result.

Batch rejections now persist in `diagnostics.sentiment_rejected_attempts`: validation
code, safe field/index, source ID, batch/attempt and a hashed classification reference.
They omit rejected quotes, arbitrary text and credentials; general logs retain metadata
only. History is capped at 16 entries with an omission count. Resolution indicates later
local batch acceptance, never verified sentiment accuracy. Completed reports and rejection
diagnostics survive specialist failure and remain in delegation artifacts; Original also
preserves completed child reports if final synthesis fails. Unknown final-answer field
errors now list missing allowlisted fields and count extra fields without storing their
arbitrary names. Existing local evidence files still contain authorized source text.

The 22 new offline regressions cover third-attempt repair, non-resetting limits,
interruption/reuse, incomplete coverage, role declines/reassignment, privacy, CLI outcomes,
canonical sources and Original -> Vanilla -> ZeroSugar integration. Scripted labels test
software contracts, not Luna's semantic accuracy. No real provider request was made for
this update; the next live run must test the repaired behavior.

## Repair feedback and retained evidence (2026-10-21)

The saved sixth run (`apinex_prueba_vanilla_6.json`, log
`20261021_140043_cc88dedfe33b.jsonl`) failed after completing 13 labels. Vanilla's later
generation hit its output limit; six Original submissions failed validation, including
two digit matches in `Q3`. No ZeroSugar review ran. This observation motivates these
changes; it does not validate the sentiment labels.

- Source-bound interpretations/proposals permit Q1-Q4, quarter/year forms and valid ISO
  dates. Other digits and the existing quantitative keywords remain restricted. Temporal
  meaning and authorized-period correspondence still require independent review.
- Citation errors distinguish list type, empty references, element type and unknown ID,
  with field and element position. Every grounded turn supplies available source IDs
  separately from fact IDs. Repair feedback is a structured object, not JSON nested inside
  an error string. It retains only allowlisted condition metadata and explicitly marks
  repeated conditions; it does not add retries or guarantee the model will correct them.
- An interrupted specialist retains evidence and reports `presentation_complete=false`.
  Original reuses its prior specialist evidence within the same scoped workflow. Vanilla
  also reports completed classifications and whether classifications remain pending.
  ZeroSugar assesses the candidate and requested coverage, not the failure flag alone.
  A completed independent review may accept recovered evidence; incomplete classification,
  missing evidence or failed integrity checks cannot be treated as completed work.
- Lime keeps its existing valid-plan reuse in Original. Chart source/column errors now
  identify their field; minimized Lime/ZeroSugar rejection histories survive correction
  or failure. Plans are still exported only after acceptance, never from partial packages.
- `verification.status` distinguishes `not_run`, `failed` and `completed` while retaining
  the existing decision field. The CLI displays that distinction. Failure metadata names
  the interrupted stage. Logs record configured output limits and available provider token
  counters before rejecting a truncated response; absent counters remain absent.

The five roles, tools, scope/privacy controls, 6000-token APInex output allowance, other
provider limits, pacing and call/turn/time budgets are unchanged. No persistent cross-run
cache, new agent or new tool is introduced. Focused offline checks are recorded in
[TESTING_AND_RAG.md](TESTING_AND_RAG.md); the full suite and live calls were not requested.

## Cited synthesis and presentation (2026-10-21)

Run seven reached two complete reviews, with all 21 blocks supported but a final `partial`
decision for redundant presentation, weak synthesis and indirect follow-up questions.
The candidate repeated a table through 11 cell sentences. Attempts to cite multiple
comments in an interpretation were rejected by the old individual-source rule. Repair
instructions also froze supported blocks, conflicting with the requested presentation repair.

The approved update uses the existing tools and five roles: `source-facts-v2` permits
qualitative synthesis across cited text sources, keeps individual excerpts literal, groups
narrative labels and removes exact table/cell repetition. Numeric calculations remain
source-bound and no prevalence is inferred from selected excerpts. The v1 replay path
preserves older artifacts. Original's repair instructions preserve facts/provenance while
allowing rephrasing and restructuring; no additional writing agent or post-review rewrite
is introduced. ZeroSugar checks all cited sources and separates mandatory `issues` from
optional `suggestions`. Existing source, completeness and safety gates still force revision.
Old review payloads without suggestions remain readable; the live tool requests the new field.

Only focused final offline checks are authorized. There is no initial baseline rerun,
full-suite run or live API call, and no change to tokens, pacing or execution budgets.
