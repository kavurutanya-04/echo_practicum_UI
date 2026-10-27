# Source-bound facts and claim review

Current review-v5, 2026-10-27, supersedes v4's literal ordered assertion reconstruction.
The original source-facts-v4 claims/IDs and all historical answer replay remain; reviews
retain short descriptions, source subsets, kinds, explicit judgments/reasons and assigned
assessment IDs. Finding-ID coverage is mechanical; atomicity, semantic coverage and
entailment remain model judgment. Literal source excerpts still require exact copying;
review claim descriptions do not. Full private capture and input-bound phase checkpoints
are documented in [RESUME_AND_CAPTURE.md](RESUME_AND_CAPTURE.md). New live validation is pending.

Current support contract, 2026-10-27: review-v4 preserves source-facts-v4 and all historical
answer replay while adding per-assertion evidence assessments. Literal visible-text
excerpts cover each finding in order; each has a source subset, factual/proposal kind,
judgment and reason. Code checks textual coverage and references, not semantic atomicity
or entailment. A failed assertion withholds its whole finding and creates an Original
repair despite an accepting model verdict. Novel proposals may go beyond source wording;
their factual premises need separate review. Stored reviews are not rewritten or given
invented assessments. See the [workflow](WORKFLOW_RELIABILITY.md#assertion-level-support-review-review-v4-2026-10-27).

After run twenty-three, complete Original analyses require a concrete reasoned action.
Its idea may go beyond the question and source wording: citations support factual
premises, while ZeroSugar assesses the proposal's rationale, assumptions and possible
benefit separately from observed facts. Existing proposal fields (quote=null), source
checks and source-facts-v4/v1-v3 replay remain. The support-only policy_requirement kind
uses request_excerpt=null for Echo's active action policy; it does not claim that the
user requested an action. See the [current workflow](WORKFLOW_RELIABILITY.md#reasoned-actions-and-review-simplification-after-run-twenty-three-2026-10-27).

After run eighteen, inactive numeric/correction assessment fields are omitted from the
support tool and supplied as empty lists by code. Active coverage, all source-facts
versions, semantic judgment and release gates are unchanged. See the
[contextual contract](WORKFLOW_RELIABILITY.md#contextual-support-review-fields-after-run-eighteen-2026-10-26).

Current guidance after run seventeen, 2026-10-26: active sentiment rubric v3 uses general
semantic definitions; historical v1/v2 identities are retained. Case-specific label
instructions were removed without changing source-facts-v4/v1-v3 replay, full released
comment context, correction request excerpts, objective data checks or acceptance gates.
Existing fixtures are aligned but unrun. See the
[current contract](WORKFLOW_RELIABILITY.md#general-semantic-guidance-after-run-seventeen-2026-10-26).

Local semantic-review update after run sixteen, 2026-10-26: source-facts-v4 and v1-v3
replay remain unchanged. New sentiment reports store the shared v2 rubric; reports
without a rubric version retain v1 replay. All canonical comments from privacy-released
groups are available as source evidence, while summary examples remain selected.
ZeroSugar receives full response/label/reason pairs and the report's rubric. Source
checks and coverage remain distinct from semantic accuracy and human validation.
New omission corrections retain exact question fragments; their relevance is model
judgment, not a literal-match proof of necessity. New coverage diagnostics contain only
counts and rubric versions. No tests, model calls or GitHub publication were performed.
See the [current contract](WORKFLOW_RELIABILITY.md#sentiment-and-correction-grounding-after-run-sixteen-2026-10-26).

Local recovery update, 2026-10-26: source-facts-v4/v1-v3 and all source gates are retained.
Repair instructions after an incomplete review are not a reviewed candidate and cannot
release findings. Original may use the remaining rounds within four total drafts, but the revised selection
requires both independent review phases. Optional review annotations may be normalized;
verdicts, finding coverage and source checks are never inferred. A current omission stays
pending until revision or justified withdrawal against the request/visible answer.
See the [recovery contract](WORKFLOW_RELIABILITY.md#review-recovery-after-run-fifteen-2026-10-26).

Diagnostic follow-up, 2026-10-26: the source-facts-v4 and v1/v2/v3 replay contracts are
unchanged. The shared validation metadata now preserves bounded/redacted structural
field names for review errors as well as grounded answers. See the [diagnostic contract](WORKFLOW_RELIABILITY.md#field-error-diagnostics-follow-up-2026-10-26).

<a id="current-v4-and-review-v2-addendum-2026-10-26"></a>

## Current v4 and review addendum (2026-10-26; correction transport updated 2026-10-27)

`source-facts-v4` preserves v3 source-fact arithmetic, quote controls and narrative review
signals, but removes the renderer's automatic data-origin claim. `source-facts-v1`, v2
and v3 retain their original text/claims on replay; v3 does not revert to numeric prose
rejection when the default advances to v4. No source facts or old artifacts are rewritten.
New chart descriptions/metadata do not presume dataset origin. Unvalidated classifier
labels and comment denominators remain substantive method limitations.

Review-v3 retains canonical corrections and assessed obligations, with explicit
mandatory/addressed judgments mapped to existing lifecycle states. Legacy v2 assessments
remain readable. See the [correction contract](WORKFLOW_RELIABILITY.md#explicit-correction-judgments-after-run-twenty-one-2026-10-27).
Earlier unconditional
issue-merging descriptions below are historical. A partial wrapper has no full selection
contract: its `verification.released_candidate` holds the reviewed selection/contract,
`released_finding_ids` identify publishable blocks, and a newer unreviewed draft is stored
separately. Published claims/evidence must match that reviewed selection. Offline audit
checks these links. See the [current workflow](WORKFLOW_RELIABILITY.md#review-and-data-contract-update-2026-10-26).

Reviewed 2026-10-23. The initial 2026-10-20 contract addresses the incorrect comparisons released in
`reports/apinex_prueba_media_actualizada.json`. The source rows were correct, but
Original wrote contradictory prose and ZeroSugar accepted it. Source replay and valid
citations did not establish entailment. A successful API call or model approval is
not a measured quality result.

## Live answer contract

Original, Cherry and Vanilla now finish live runs through `submit_grounded_answer`.
The model selects existing `fact_ids` and supplies provisional individual interpretations or cited syntheses
or proposed actions. Free-form final answers, invented IDs and changed controlled facts
are rejected locally, with bounded repair attempts. In v3, narrative quantities and
quantifiers generate review signals rather than automatic rejection.
Scripted demos retain their fixture path and are not live quality evidence.

`agents/grounding.py` builds a fact catalog from the current scoped evidence. Each fact
has its original source IDs, scope, operation, source metric metadata and stable ID.
Observed numeric cells preserve their original row/column/value and known unit.
Exploratory SQL explicitly retains an unvalidated metric-meaning label: a successful
query is not proof of correct grain, denominator or question mapping.

For catalog survey trends, Python computes adjacent-date and first-to-last changes,
point-in-time differences between dimensions and higher/lower/equal coverage across
matched dates. It never turns missing values into zero or infers causal effects.
Directions, dates, values and score-point/percentage-point units are rendered by code.
Matching dimensions also get a combined source table; individual tables remain available.
Tables and their citations are one explicit review unit, independent of blank paragraphs.
The catalog is bounded at 1024 facts; a response may select at most 24 facts and 32 total
claims including narrative and limitations. Overlarge requests fail explicitly rather
than silently dropping source records. One through six dimensions, including an eight-quarter
scope, are covered by offline regression checks.

Tables and measured comparisons select these facts rather than recomputing them in prose.
Brief narrative references may reuse cited values and receive semantic review. Cherry keeps
its read-only metric/schema/SQL tools and selects only numeric source facts. Typed
delegation restricts Cherry to `numeric` and Vanilla to `text`/`sentiment`; it does not
make arbitrary natural-language task interpretation infallible.

New answers use `source-facts-v4`. If an exact source table and its individual numeric
cells are selected together, the renderer displays the table and omits only the repeated
cell sentences. Calculated comparisons remain separate. Numeric facts, operations and
source IDs remain unchanged. Stored `source-facts-v1`, `source-facts-v2` and `source-facts-v3` answers replay
with their original rendering and validation rules; new normalization and review signals
are not imposed on older artifacts.

## Text and proposed actions

Vanilla's complete-population sentiment classifications remain provisional. Python
checks unique source coverage, exact excerpts up to 400 characters and recomputed
counts/percentages; those checks do not establish label semantics. Ranked passages
still cannot support prevalence estimates.

In v3, a supplied `quote` explicitly represents a literal example and must occur exactly
in a cited text source. An interpretation uses `quote=null`, with one or several sources
containing text or source rows; a sentiment summary may be interpreted through its
`SENTIMENTn` citation. Source count does not decide whether an excerpt is mandatory.
ZeroSugar checks requested example coverage, meaning, disagreement and unsupported
generalization. Each normalized narrative item is one review unit, including a short
multi-sentence item. Tables/calculations still select source facts; quantities and
quantifiers in prose are provisional statements for semantic review, not automatically
reproducible calculations. Proposed intervals/targets remain proposals, never observations.
Literal quotes alone do not prove entailment.
Interpretation and proposed-action/question labels appear once per section. Requested
follow-up questions are authored as direct questions by the model. The same rendered
candidate is reviewed and released; there is no second unreviewed writing pass.
Partial output retains the provisional/proposal disclosure even if the first block carrying
a section label is withheld; that disclosure adds no new analytical claim.
V3 normalizes whitespace/newlines, known inline citations and source-ID wrappers without
changing quoted source characters. Known inline citations move to the item's references.
Ordinary prose brackets are escaped for display; explicit unknown source IDs still fail.
Missing, malformed and unknown citation references retain field/index errors. The older
v1/v2 numeric restrictions, including their date exceptions, remain on saved replay paths.

Complete sentiment summaries also expose their publishable example responses as separate
`survey_response` evidence. These use the existing comment citation ID, canonical response
text (not the question plus a search excerpt), scope and anonymous provenance. A canonical
response replaces an earlier search excerpt with the same ID, rather than creating two
conflicting source records. Vanilla and Original cite that text for interpretations;
the `SENTIMENTn` ID supports the aggregate table and its provisional interpretation. ZeroSugar compares canonical evidence
with the trusted scoped response and checks whether an excerpt entails its interpretation.
Full labels/source hashes remain in the local sentiment report; this bridge neither
reclassifies comments nor turns source integrity into semantic validation.

## Independent review and release

ZeroSugar receives the explicit claims, original evidence, coverage metadata and v3
`review_warnings`. Its payload also includes up to 64 relevant code-computed comparisons,
prioritizing selected facts and reporting any omitted count; the full cited source rows
remain evidence. Python independently rebuilds the catalog and rendered answer, detecting
altered controlled cells, signs, dates, units, source IDs or claim text. Replay confirms
reproducibility, not the truth of a model-authored numerical sentence. ZeroSugar
still reviews task completeness, SQL semantics, interpretation, uncertainty, omissions
and safety. Each claim has its own finding decision; the verifier cannot rewrite it.
Original may rewrite, reorder or remove duplicate presentation while preserving supported
facts, meaning and provenance; each revised candidate goes through review again. The
review's `issues` are mandatory corrections; `suggestions` are optional and do not alone
force revision. Missing requested synthesis/questions and unsupported meaning remain issues.

The 2026-10-23 update retires the mandatory deliverable checklist and preserves the answer
payload/replay versions. ZeroSugar first reviews the question and exact visible answer
without evidence, then reviews sources/claims and prior corrections in a separate call.
The first verdict's omissions remain mandatory even if the support stage accepts. Every
revised package undergoes both calls. Source-review outputs identify findings by ID; the
application retains their original citation IDs. Old finding submissions with citations
are still checked when supplied. New phase traces contain metadata only, not copied user
requests or comments. Actual corrections remain local; no checklist field is required in
new plans. See the [current workflow](WORKFLOW_RELIABILITY.md#autonomous-synthesis-and-two-stage-review-2026-10-23). These controls do not prove semantic correctness.

Narrative warning markers never enter `deterministic_issues`. ZeroSugar explains the
flagged claim's support or uncertainty in its existing per-finding reason, checking value,
direction, unit, denominator, period and population as relevant. It uses computed facts
instead of recreating inequality chains in free prose. Its judgment remains fallible;
no further model automatically reviews an accepted verifier rationale. V3 records warning
assessment outcomes, not a claim of validated semantic accuracy.

Rejected narrative items now retain bounded redacted text/quote/reference context and the
actual application feedback in local JSON/JSONL. Normalizations retain before/after context;
warning records identify the phrase, trigger and review outcome. Recognizable credential
and identifier patterns are redacted; unknown fields/full provider payloads are omitted.
Pattern redaction is not comprehensive personal-data detection. Artifacts remain local.

This first-stage update follows run nine's repeated answer-validation failures. No tests
or model/API calls were run for it, by user instruction. Historical offline results below
predate v3; successful live confirmation remains pending. Specialist handoff simplification
is a separate second-stage proposal, not implemented by this update.

The existing partial-release gates remain: only independently supported claims may be
released, incomplete sentiment never yields percentages, and a deterministic integrity
or safety failure prevents partial release. Rejected drafts and claims remain local
diagnostics, not approved findings. All five roles are preserved; Lime still handles
only source-backed chart plans.

The contract does not guarantee zero model errors or validated custom-query/label
semantics. Exploratory query meaning and textual interpretations still need evaluation
against independent human judgments. Prompt/catalog selection can also omit needed
facts; ZeroSugar must check the original question, not merely the selected facts.

## Offline audit and human evaluation

```powershell
python -m unittest discover -s tests -p test_grounded_claims.py -v
python audit_grounding.py reports/apinex_prueba_media_actualizada.json --output reports/grounding_review.json
```

The audit calls no model. It replays source checks and prepares per-role review packets,
reference survey trends, exploratory queries and, when preserved labels exist, annotation
examples with empty human-label fields. It includes textual source examples for reviewing
Vanilla's interpretations. Its diagnostic sample is not an unbiased benchmark sample.
Old narrative-only artifacts are explicitly flagged for manual semantic review; they are
not retroactively certified by the new contract. If labels were never preserved, the
audit says classification quality cannot be assessed from that artifact.

All classifications and interpretations remain provisional even when their quotes are
literal. The tests deliberately separate excerpt validity from semantic accuracy. The
new numerical controls cover recorded source cells and the implemented survey operations;
they are not a general natural-language truth detector for arbitrary SQL or narratives.

The first audit covered four existing local artifacts and 13 role executions, including
Original, Cherry and Vanilla. None contained preserved complete classification labels,
so no classifier accuracy was calculated. Human entailment review is pending. The packet
is `reports/grounding_audit_before_upgrade.json` and is excluded from Git, alongside all
source-bearing reports. No new live API test was run for this upgrade. Input catalog size
and actual provider behavior/cost must be checked in the next live test; local regression
success is software evidence, not a model quality benchmark.

Follow-up, 2026-10-21: the user's fourth live Luna run completed with nine calls, a cited
comparison table and source-reproducible numerical claims accepted by ZeroSugar. Vanilla
was not invoked, so this does not evaluate text/sentiment quality. Four source-submission
attempts required correction. The subsequent diagnostic update preserves minimized
rejected-only records in `diagnostics.rejected_attempts`, without full rejected prose or
tool payloads; its exact retention/privacy boundaries are in
[WORKFLOW_RELIABILITY.md](WORKFLOW_RELIABILITY.md#rejected-source-answer-diagnostics-2026-10-21).
At that diagnostic-only stage the proposal digit rule was unchanged and reported as a
syntactic restriction, not proof of hallucination. Diagnostic-only replay preserved the fourth accepted answer
and claims exactly, without another provider call.

The fifth Luna run then failed before ZeroSugar: complete labels existed inside a Vanilla
delegation, but canonical comment evidence was not available to the final response path.
The subsequent source bridge described above exposes individual response text without
relaxing literal-quote validation or reclassifying the population. Three bounded batch
attempts and retained same-workflow progress address retries separately from claim review.
That implementation passed 207 offline tests. The sixth run later failed during final
response construction; the subsequent repair has focused offline coverage only. See [current results](PROJECT_CONTEXT.md),
[testing directions](TESTING_AND_RAG.md) and the [reference map](DOCUMENTATION_MAP.md).
