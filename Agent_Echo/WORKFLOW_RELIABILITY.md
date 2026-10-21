# Workflow reliability: current execution and repair contracts

Reviewed 2026-10-21 against the current runtime and the fifth-run repairs. Earlier dated
sections retain their original change context; the current contracts below and the
[documentation map](DOCUMENTATION_MAP.md) identify the relevant implementation sources.

The five roles and final GW Azure default are retained. All manager-facing output is
English. This change does not add a UI, authentication system, bilingual testing or a
comparative provider benchmark. Later dated changes below supersede historical contract
details where explicitly stated.

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
