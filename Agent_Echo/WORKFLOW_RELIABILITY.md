# Workflow reliability: points 3–9

The five roles and final GW Azure default are retained. All manager-facing output is
English. This change does not add a UI, authentication system, bilingual testing or a
comparative provider benchmark.

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

The final turn has no tools and asks for an evidence-based answer or explicit limitation.
Each turn states the remaining allowance. Identical tool requests reuse their result within
that run and trigger closure only when no planned Cherry metrics remain unresolved.
Hard turn/tool/time limits still force bounded closure with explicit limitations. A failed or
noncompliant model produces an explicit failure instead of invented conclusions.

## 5. Selective roles

Original submits a typed plan: numeric evidence, text evidence, optional chart or a
necessary task clarification. Only planned specialists are available. Simple counts can
skip Vanilla and Lime. Analytical findings still require ZeroSugar review. Clarification
responses contain no analytical findings.

## 6. Localized repairs

ZeroSugar selects repair targets: Cherry, Vanilla, Lime, Original or clarification. The
single correction pass permits only affected specialists. Chart-only repairs reuse the
candidate and calculations. Unchanged chart plans are reused when another role is repaired.
Sources and the final package are still reviewed. Nothing is cached across executions.

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
The reviewer cannot rewrite the text into a new claim. Missing/repeated findings or changed
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
sentiment percentages. Charts are withheld for incomplete packages. Known failures also
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

Planning diagnostics log validation codes/field names, not prompt or justification text.
The optional ignored JSON artifact records the accepted clarification basis. Regression
checks in [test_clarification_policy.py](tests/test_clarification_policy.py) exercise these
paths using scripted responses, not provider reasoning. The user's third APInex run
(`reports/apinex_prueba_media_3.json`) stopped after one planning call with an unnecessary
clarification; this update has not yet been evaluated in another live run. Interactive
terminal continuation, natural-language date resolution and authenticated manager selection
remain deferred; `run_agent.py`, connections and request pacing are unchanged.

## 9. Diagnostics

Automatic local JSONL logs include plan choices, skipped roles, remaining budgets,
closure, request fingerprints, cache hits, metric execution/replay, finding decisions,
repair targets and final response status. They exclude raw queries, prompts, answers,
employee records, credentials and provider payloads. Optional local artifacts retain the
detailed evidence and `diagnostics.last_unverified_text` after a formatting failure; this
diagnostic text is never a released finding. Known citation wrappers are normalized without
creating new source records. Provider null sentinels are handled as absent values, not questions. All reports/logs remain ignored by Git.

Structured validation errors additionally record a stable validation code, field path,
record index and known source/finding ID where applicable. Literal quote mismatch and
quote length are separate failures. Reviews report missing rubric dimensions, finding
coverage, invalid fields and changed citations through separate codes. No rejected quote
text or arbitrary provider exception is written to the execution log.

Vanilla permits exact contiguous quote excerpts of 1-400 characters; 400 is a maximum,
not a requested length. Explanations remain capped at 160 characters. Classification uses
20-comment batches and at most two attempts per batch. Valid records are retained while
only unresolved comments and bounded error reasons are sent in a fresh repair request.
No partial sentiment percentages are produced. Local schema/quote checks establish
provenance and completeness, not semantic label accuracy.

Behavioral tests cover duplicates, parameter binding, closure, reuse, role selection,
localized correction, finding coverage and safe partial release. These implementation
checks do not replace the deferred comparative live evaluation.
