# Source-bound facts and claim review

Reviewed 2026-10-21. The initial 2026-10-20 contract addresses the incorrect comparisons released in
`reports/apinex_prueba_media_actualizada.json`. The source rows were correct, but
Original wrote contradictory prose and ZeroSugar accepted it. Source replay and valid
citations did not establish entailment. A successful API call or model approval is
not a measured quality result.

## Live answer contract

Original, Cherry and Vanilla now finish live runs through `submit_grounded_answer`.
The model selects existing `fact_ids` and supplies individual provisional interpretations
or proposed actions. Free-form final answers, invented IDs, changed values and numerical
claims in interpretation fields are rejected locally, with bounded repair attempts.
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

Original selects these facts rather than recalculating or paraphrasing them. Cherry keeps
its read-only metric/schema/SQL tools and selects only numeric source facts. Typed
delegation restricts Cherry to `numeric` and Vanilla to `text`/`sentiment`; it does not
make arbitrary natural-language task interpretation infallible.

## Text and proposed actions

Vanilla's complete-population sentiment classifications remain provisional. Python
checks unique source coverage, exact excerpts up to 400 characters and recomputed
counts/percentages; those checks do not establish label semantics. Ranked passages
still cannot support prevalence estimates.

Qualitative interpretations require actual supplied text evidence, literal excerpts
and one explicit source ID per interpretation. They are rendered as provisional interpretations for manager
review. Multi-sentence text is separated into individual review units. Quantified
population claims must use source facts, not interpretation prose. Proposed actions
are labeled as proposals rather than observed outcomes; invented numerical targets
are not allowed in that field. Literal quotes alone do not prove entailment.
The 2026-10-21 repair permits quarter/year references and valid ISO dates in these
sentences; it does not permit analytic quantities or certify temporal meaning. Missing,
malformed and unknown citation references now receive separate field/index errors.

Complete sentiment summaries also expose their publishable example responses as separate
`survey_response` evidence. These use the existing comment citation ID, canonical response
text (not the question plus a search excerpt), scope and anonymous provenance. A canonical
response replaces an earlier search excerpt with the same ID, rather than creating two
conflicting source records. Vanilla and Original cite that text for interpretations;
the `SENTIMENTn` ID supports the aggregate table. ZeroSugar compares canonical evidence
with the trusted scoped response and checks whether an excerpt entails its interpretation.
Full labels/source hashes remain in the local sentiment report; this bridge neither
reclassifies comments nor turns source integrity into semantic validation.

## Independent review and release

ZeroSugar receives the explicit claims, original evidence and coverage metadata. Python
independently rebuilds the catalog and rendered answer, detecting altered cells, signs,
dates, units, source IDs or text before a model approval can release them. ZeroSugar
still reviews task completeness, SQL semantics, interpretation, uncertainty, omissions
and safety. Each claim has its own finding decision; the verifier cannot rewrite it.

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
