# Echo agent responsibilities and examples

Current contract, 2026-10-27: review-v5 corrects B after runs 27-29. Original expresses
reviewable assertions using existing source-linked items; ZeroSugar judges their meaning
with concise claim descriptions, without reproducing tables/formatting. Code assigns
assessment IDs and still withholds an entire finding on a failed assertion. No role was
added. Phase-only retries preserve the producer's retained work; a review retry calls
ZeroSugar alone and stops at its decision. See [the current contract](RESUME_AND_CAPTURE.md).
Its capture/resume changes and aligned regressions are unrun, per user instruction.

Current support contract, 2026-10-27: review-v4 adds explicit assessments for individual
assertions inside each finding. ZeroSugar supplies literal claim excerpts, factual/proposal
kind, source subsets, judgment and reasons. Code checks coverage/references and withholds
any finding containing a contradicted or insufficient_evidence assertion. Original receives
the repair and assessments. Novel action ideas remain proposals; their factual premises
are reviewed separately. V3 correction judgments, five roles and both phases remain.
See the [current contract](WORKFLOW_RELIABILITY.md#assertion-level-support-review-review-v4-2026-10-27).

Current correction contract, 2026-10-27: review-v3 requests code-keyed mandatory/addressed
judgments and reasons instead of lifecycle states or replacement IDs. ZeroSugar still
owns the semantic judgment; code derives and preserves the existing state/routing/export
shape. A current objection judged already addressed is withdrawn; a real visible omission
judged required and unaddressed stays pending. Legacy v2 submissions retain the guards
described below. See the [current contract](WORKFLOW_RELIABILITY.md#explicit-correction-judgments-after-run-twenty-one-2026-10-27).

Local recovery update, 2026-10-26: ZeroSugar distinguishes annotation normalization,
pending repair and completed review. A current correction submitted as resolved stays
pending; false omissions can be withdrawn against visible content. Invalid support
submissions may return validated repair instructions to Original without an approval,
within a four-draft limit (initial plus three revisions), including recovery after the
second or third draft. ZeroSugar retains three attempts per phase; both phases are
required before acceptance. Shared model/time/tool budgets still take precedence.
Completeness sees trusted manager/date/team context, not source evidence. Cherry and
Vanilla retain team authorization context from their scoped backend; Original passes it
through and distinguishes selected examples from totals. Roles and budgets are retained.
See the [recovery contract](WORKFLOW_RELIABILITY.md#review-recovery-after-run-fifteen-2026-10-26).

Diagnostic follow-up, 2026-10-26: ZeroSugar's structured field rejections now preserve
missing/additional keys, types and positions through model feedback and bounded local
records. Retry identity and valid-submission repair events distinguish transport repair
from analytical acceptance. This does not change the roles or review judgments. See the
[diagnostic contract](WORKFLOW_RELIABILITY.md#field-error-diagnostics-follow-up-2026-10-26).

## Current coordination contract (updated 2026-10-27)

After run twenty-three, Original's complete analytical answer includes all requested
content plus at least one concrete manager action reasoned from the analysis. New ideas
are allowed beyond the question/source wording; factual premises remain source-grounded
and benefits/assumptions are proposals. Completeness checks user-requested visible work;
support separately receives the active Echo action policy and judges its fulfillment.
Its policy_requirement correction belongs to Original with request_excerpt=null, avoiding
a fictitious user request. Specialist diagnostics do not inherit this policy by default.
The simplified review instructions retain objective gates and correction reassessment.

All five roles analyze supplied data independently of its origin. Original distinguishes
its internal analysis plan from manager-facing proposed actions, choosing depth and
presentation without mandatory targets/resources/checklists. Cherry retains numeric
ownership; Vanilla retains text/classification; Lime retains visualization. ZeroSugar
retains separate completeness/support review and independently reassesses actual
corrections, including justified withdrawal; consolidation remains a legacy v2 mechanism.
Source/scope/privacy gates cannot be withdrawn by model judgment. New reviews use `review-v3`, deriving routing from
one correction list and assessing pending numeric relevance. New answers use v4; older
answer contracts remain reproducible. See the [current workflow](WORKFLOW_RELIABILITY.md#review-and-data-contract-update-2026-10-26).

After run twenty-two, Original explicitly fulfills requested content and item counts
while keeping useful actions as additions. Each action explains how a cited finding
motivates addressing a problem or sustaining a strength, without claiming measured
impact. Both ZeroSugar phases distinguish team questions from action recommendations
by meaning, not punctuation; useful extra content cannot make a real omission optional.
Support also assesses the proposed action's connection to findings. Unjustified
objections remain withdrawable through review-v3; no stage or checklist was added.

The [workflow reliability update](WORKFLOW_RELIABILITY.md) supersedes unconditional role
execution and all-or-nothing release described below: Original now plans required roles,
Cherry offers validated metrics, ZeroSugar reviews cited blocks, and only supported blocks
can appear in a partial answer. Output is English. Lime runs only when a chart is planned.

Live Original, Cherry and Vanilla answers now follow the [source-bound claim contract](SOURCE_GROUNDING.md): models select existing facts, code renders numeric statements/tables, and ZeroSugar reviews explicit claims. Text interpretations and sentiment labels remain provisional rather than semantically certified by citation checks.
The current `source-facts-v4` contract permits interpretations across one or several cited
text/row sources with `quote=null`. Explicit examples still require literal excerpts. Original may revise
wording/layout while preserving facts, meaning and provenance; every candidate is reviewed.
Exact source tables replace repeated individual-cell sentences, and labels are grouped.

Updated 2026-10-23. Five roles share configurable model adapters; each has its own instructions and history. This is a terminal/local-file prototype. The bundled dataset is synthetic; runtime analysis does not presume data origin. Descriptions below complement the executable `INSTRUCTIONS` in each agent file.

The 2026-10-23 update removes the mandatory per-question checklist, retains actual review
corrections and introduces separate completeness/support calls within ZeroSugar. See the
[current workflow](WORKFLOW_RELIABILITY.md#autonomous-synthesis-and-two-stage-review-2026-10-23). The five roles and specialist formats remain.

## Semantic-review update after run sixteen (2026-10-26)

After run eighteen, ZeroSugar's support tool requests numeric_reviews/correction_reviews
only when trusted pending requests/obligations exist. Echo supplies inactive lists as
empty without inferring judgments. Active assessments, full comment context and both
review phases remain required. See the [contextual contract](WORKFLOW_RELIABILITY.md#contextual-support-review-fields-after-run-eighteen-2026-10-26).

Following the user's run-seventeen review, Vanilla now uses shared `survey-sentiment-v3`
with general definitions and contextual model judgment. No case-specific combination of
praise, criticism or closing words forces a label. Stored v1/v2 definitions remain for
historical review; classification and verification share the report's rubric identity.
Its tool continues to supply all canonical responses in
privacy-released groups. ZeroSugar support sees each full response, label, excerpt and
reason with that report's rubric. Suppressed
texts remain excluded. Coverage counts do not establish semantic accuracy or imply zero
indeterminate comments. All labels remain unvalidated by humans.

New omissions require literal request_excerpt grounding; factual repairs must name the
claim and conflicting evidence. Original challenges unjustified changes; ZeroSugar uses
the existing withdrawal/consolidation/reassessment lifecycle. Full sources, valid inline
IDs and explicit denominators can satisfy a request without a prescribed format or
examples for unrequested categories. No new role or model call stage was added. This
update is local and untested at the user's request. See the
[workflow](WORKFLOW_RELIABILITY.md#sentiment-and-correction-grounding-after-run-sixteen-2026-10-26).

## Original — coordination, synthesis and supervised revision

**Input:** manager question, backend-fixed manager/date scope, specialist responses and verifier feedback. **Tools:** `ask_cherry(question, task_type="numeric")` and `ask_vanilla(question, task_type="text"/"sentiment")`; source-fact selection uses `submit_grounded_answer`. **Output:** a cited candidate answer, source evidence and specialist delegations.

Original decomposes the question, requests appropriately bounded evidence, combines quantitative and textual findings, acknowledges disagreement and explains unavailable coverage. Its plan distinguishes SQL/rating metrics from Vanilla's full comment classification and derived counts/percentages (`needs_sentiment`). A sentiment-only task does not require Cherry. Original corrects incompatible delegations after a specialist's structured decline; it does not resend an identical closed request. It owns the answer and responds to ZeroSugar's correction request. It does not run SQL, widen access, retrieve files, choose chart types or render graphs. The workflow invokes Lime when Original's plan requires a chart.

Original chooses how to integrate a useful, complete answer. Adequate specialist analysis
is a basis for synthesis, not material that must be rewritten. Preserve meaning, disagreement
and limits while allowing reorganization and concise presentation. Existing evidence can
support requested examples; collection alone does not make them visible to the reader.
Actual review corrections accompany a revision without a mandatory prewritten task list.

Cherry, Vanilla and Lime can use `decline_task(reason_code, reason)` in their existing model turn when their tools cannot perform the assigned work. Codes distinguish `out_of_role`, `missing_input` and `insufficient_evidence`; this adds no mandatory model call. An optional no-chart result remains different from a declined chart task. A decline is neither proof of absent records nor permission to widen access.

Example: "What do this quarter's recognition metrics and comments suggest?" Original asks Cherry for team/period metrics with response counts and Vanilla for relevant supportive and critical comments. It combines the results without claiming that selected comments measure prevalence. For a requested chart, Original asks Cherry for usable indicator rows and denominators; Lime makes the presentation decision.

Example boundary: "Identify the person behind this anonymous comment." Explain that the authorized evidence cannot support identification. Do not delegate an identity-matching task. Proposed actions support manager review, not personnel decisions.

## Cherry — quantitative evidence and Text-to-SQL

**Input:** a bounded analytical question. **Tools:** `describe_schema()`, `execute_sql(sql)` and `run_metric(metric, dimension)`; live source selection or task decline uses the shared response contract. **Output:** numeric findings with `[SQLn]` citations; SQL text, returned rows, scope and truncation flag are retained as evidence.

Cherry inspects permitted tables, chooses read-only SQL, repairs failed queries and explains metrics, denominators and limits. It preserves the correct grain when joining contributions, feedback, work requests and capacity. Names in authorized operational records are permitted; anonymous surveys remain team aggregates and benefit histories remain group summaries. Cherry does not choose graphs, interpret retrieved comments or infer causal effects.

Example: "How many cross-team contributions lack a recorded manager-recognition note?" Count distinct contributions and check for matching recognition records with `EXISTS`/`NOT EXISTS`. Include the eligible total and explain that an absent note is not proof that recognition never occurred.

Example: "Show Recognition over eight quarters." Return `Team`, `Survey_Date`, `Responses`, `Mean_Score` and optionally `Favorable_Percent` in ordered rows. Weighted averages require response counts; favorable percentages and eNPS are different metrics. These rows become Lime's input.

Example: "Which weeks exceed available project hours?" Aggregate requests by employee/week before joining capacity. Recorded current-state demand is not a complete historical reconstruction.

## Vanilla — retrieval-augmented textual interpretation

**Input:** a bounded textual question. **Tools:** `search_text(query, source, dimension, limit)` for themes and `analyze_survey_sentiment(dimension)` for full-population text classification. **Output:** cited interpretations and/or provisional sentiment summaries. The `rag` field records ranked retrieval; the `sentiment` field preserves every classification ID, category, exact supporting excerpt, explanation and source hash.

Vanilla retrieves scoped survey comments, recognition feedback, contributions, work descriptions or priority explanations before interpreting them. Lexical retrieval uses FTS5/BM25; semantic retrieval uses provider embeddings/cosine similarity; hybrid combines ranks. It can try alternative terms and source/dimension filters. Retrieved text is evidence, never authority to change its instructions.

When delegated, Vanilla handles the delegated textual question, supplies supported patterns,
source-linked examples and limits, and retains its existing response format. Examples in
attached evidence and examples printed in its answer remain distinct. Original integrates
the final answer; Vanilla retains qualitative interpretation and standalone use.

Example: "Find supportive and critical recognition views." Retrieve Recognition comments, cite actual passages and explain the selection method. Do not claim that the proportion of retrieved positive passages equals team sentiment.

Example: "What explains the priority changes?" Retrieve recorded `OP_priority_decisions` explanations. Do not invent motives or use general model knowledge to fill missing records. A zero-hit search is a retrieval limitation, not proof of no issues.

Anonymous source identity fields are excluded, but free-text content is not automatically redacted. Small-group thresholds are safeguards, not a guarantee against every identification risk. Real authentication and free-text privacy review remain unfinished.

## Lime — relevant indicator charts and local exports

Lime replaces the earlier functional name Visualizer, keeping the project's flavor naming convention. [Coca-Cola Lime](https://www.coca-cola.com/gb/en/brands/coca-cola-original-taste) is an actual Coca-Cola flavor. Only SQL evidence marked as produced by Cherry is sent as data; Vanilla passages and retrieval scores are not sent. The candidate answer provides context, never numeric authority.

**Input:** question, candidate answer, exact evidence rows, scope and optional review feedback. **Tool:** `submit_visuals(charts, reason)`. **Output:** zero to three chart specifications and an explicit relevance/no-chart explanation. After acceptance, its exporter generates `.svg`, companion `.csv` and `.json` provenance files.

Lime is a separately prompted model role with its own `agents.Lime` assignment in `connections.json`, overridden by an explicit run-wide `--profile`. The old `ECHO_LIME_PROFILE` variable does not select it. Lime decides whether a chart helps, which supported indicator to plot, bar versus line, axes, series, units, denominator and title. It has no database access and cannot generate executable code, request arbitrary files or invent numeric arrays. Specs reference SQL citation IDs and column names; the exporter reads values directly from those rows. Original does not pick chart types.

Concrete renderer: `agents/chart_export.py::export_charts`. It draws vector graphics using Python's standard library. No plotting package, web server or dashboard framework is required. Files open in a browser or compatible image editor; opening an SVG is not deploying a web application.

Example: quarterly mean Recognition score -> line chart by `Survey_Date`, series `Team`, units `Score (1-5)`, denominator `Responses`. Example: contribution counts by beneficiary team -> bar chart from Cherry's computed counts. Example: comment examples without a numeric table -> no chart, with an explanation. Counts are not percentages; ranking text or embedding similarity is not an engagement indicator.

The validator rejects unknown sources/columns, mismatched scope, truncated tables, nonnumeric/nonfinite values, duplicate category/series pairs and means/rates without source denominators. Limits are three charts, 48 complete source rows per chart, six series, 24 temporal categories or 18 bar categories. Nulls remain missing; the renderer does not aggregate or calculate new metrics. A limitation can be addressed by requesting a better aggregated result from Cherry on the workflow's revision.

## Survey sentiment: implemented workflow and pending quality evaluation

Vanilla now has explicit instructions and an executable `analyze_survey_sentiment` tool. It enumerates every authorized survey comment in the fixed manager/date scope, optionally restricted to one dimension; it does not rank, sample or deduplicate identical responses. The existing survey-response threshold still applies. The configured Vanilla model labels batches of 20 comments as positive, negative, neutral, mixed or indeterminate. Definitions and examples are in its executable rubric. Numeric response scores and identity tokens are omitted from classification input. Unclear or empty responses must not be guessed.

Code validates complete unique-ID coverage and exact response excerpts, then computes counts/percentages by team, survey date and dimension. Each percentage uses all eligible comments in that group, including indeterminate and mixed labels. Groups below five comments and their examples are suppressed in the summary. These are comment percentages, not employee percentages. The JSON artifact retains the full labels/source hashes in `sentiment`; generated outputs remain ignored by Git.

Supporting excerpts must copy exact contiguous response text, including punctuation and relevant negation, up to 400 characters; label explanations remain limited to 160 and may paraphrase. A quote is never a summary, translation or interpretation. Python validates these rules without an API call. Errors distinguish length, nonliteral excerpts, unknown/duplicate/missing IDs and invalid labels. During the three bounded attempts for a batch, valid records are retained and only unresolved comments are resubmitted. If those attempts are exhausted, Vanilla returns incomplete progress with validated/pending counts and IDs, never partial percentages.

Example: "What percentage of Recognition comments is negative this quarter?" Original delegates this to Vanilla with an explicit request to use the classification tool. Vanilla returns `[SENTIMENT1]` evidence with the population, denominator, all five category counts, percentages and the human-validation limitation. ZeroSugar rechecks source hashes, IDs, coverage, quotes and recomputed summaries; its model reviews supported claims and source-linked example labels. These checks do not establish the semantic correctness of every label.

The summary's publishable example comments are also registered as individual canonical `survey_response` evidence, containing the authorized response text and existing citation IDs. Vanilla and Original can cite those records in interpretations; `SENTIMENTn` remains the aggregate table source. ZeroSugar independently reloads the scoped response, checks exact content/provenance and reviews its meaning. No second classification is required to expose those citations.

Large scopes require more model calls than a simple answer. Before starting, the tool checks whether all remaining batches fit the caller budget. Narrow the dates/dimension or explicitly raise `--model-call-limit` and `--run-seconds`; it never substitutes partial percentages. A failed batch or exhausted budget produces no completed sentiment result. Valid labels and batch-attempt counters survive redelegation within one Original workflow for identical scope/source/model/rubric inputs; changing the delegated wording does not reset the three-attempt limit. Independent runs reset progress. Existing global call, turn, time and pacing limits still apply.

The fifth Luna run produced a complete classification report inside a delegation but failed before independent review or release. It does not establish label quality. No human-labeled comparison, per-category precision/recall or measured classifier accuracy exists yet; `human_validated=false` is fixed in the summary. The routing/retry/source repairs have offline regression coverage; a new live test is pending. Human evaluation still requires a held-out sample covering every category and dimension, comparison with independently assigned labels, and inspection of disagreement and abstention. Numeric survey ratings remain a separate signal.

Lime still accepts only Cherry's SQL evidence. It therefore does not chart these Vanilla summaries in this update; a future sentiment-chart path must give Cherry a verified derived table rather than passing Vanilla data directly to Lime. No frontend or extra agent is added.

## ZeroSugar — independent answer and chart-plan review

Pending-correction coverage is enforced. Review-v3 requires every code-provided
correction_judgments key with explicit mandatory/addressed booleans and a reason; the
model does not construct IDs or choose replacement relationships. Legacy v2 submissions
retain correction_reviews coverage and consolidation checks. Both remain fallible model
judgments about semantic completion, never source-integrity overrides.

**First input:** original question, visible candidate answer and presentation labels for
accompanying charts, with no source data. **First tool:**
`submit_completeness_review`, with completeness score, decision, rationale, mandatory corrections
and optional suggestions. **Second input:** answer, scoped sources, claims, chart plan,
objective checks, completeness verdict and prior corrections. **Second tool:** `submit_review`
with seven-dimension ratings, per-block decisions/reasons and correction feedback. Code
combines both reviews; source acceptance cannot erase a visible-answer omission. New finding
reviews identify the block; its citation IDs are attached by code instead of recopied by the model.

ZeroSugar checks citations, manager/date scope, anonymous identity fields, SQL replay, text/source correspondence and chart schema. Its model checks whether claims and chart labels are supported, whether the indicator addresses the question and whether units/denominators match. It does not write the answer or generate new metrics. Code forces revision for deterministic failures even if the model accepts.
For a synthesis it checks all cited text sources, including contrary evidence. Mandatory
corrections belong in `corrections` (code derives `issues`), optional improvements in `suggestions`; optional suggestions
alone do not block acceptance. Missing requested synthesis/questions remain mandatory.
Lime's SQL-only input, Cherry's calculations and Vanilla's classification tools are unchanged.

First-stage v3 update, 2026-10-21: Original/Vanilla may interpret cited text or numeric
rows with `quote=null`, including a single source. A supplied example quote remains literal.
Narrative digits/quantifiers become nonblocking review signals; ZeroSugar explains their
support, units, denominator, period and population in the affected finding reason. Relevant
computed comparisons are supplied, so the reviewer need not reconstruct inequality chains.
Code checks structure, provenance, coverage and structured arithmetic, not whether an
opinion is positive or a conclusion is meaningful. Bounded redacted rejection/normalization
context and warning assessments remain local. No tests or API calls were run for this
update. The separate proposal to remove mandatory specialist presentation is not implemented.

Example rejection: a title claiming causal engagement improvement from unsupported associations; an average labeled as a percentage; a chart built from truncated rows; invented sentiment prevalence from selected comments. Example acceptance: supported findings with source references, an appropriate chart and honest limitations, or a justified no-chart result.

One localized correction round is allowed. A rejected full draft is withheld; independently supported blocks can be released as a partial answer. Charts remain withheld for incomplete packages. Model judgment remains fallible. ZeroSugar reviews structured specs and data, not a rendered image; human visual inspection is separate.

Recovery update, 2026-10-21: interrupted Cherry/Vanilla executions can retain evidence
without a completed presentation. Original supplies that outcome to ZeroSugar, which
must review the candidate and remaining coverage before release. A failure flag alone
does not invalidate complete evidence; neither retained evidence nor a literal quote is
approval. Lime keeps valid-plan reuse, and Lime/ZeroSugar now retain minimized repair
diagnostics. See [the shared contract](WORKFLOW_RELIABILITY.md#repair-feedback-and-retained-evidence-2026-10-21).

## Workflow

```mermaid
flowchart TB
    Q[Manager question] --> O[Original: coordinate and synthesize]
    O <--> C[Cherry: numeric evidence]
    O <--> V[Vanilla: retrieved textual evidence]
    O --> P[Candidate answer and source evidence]
    P --> D{Chart planned?}
    D -->|Yes| G[Lime: choose supported charts or return task outcome]
    D -->|No| Z
    G --> Z[ZeroSugar: review answer, evidence and chart plan]
    Z -->|One correction round| O
    Z -->|Accept| E[Lime exporter: local SVG, CSV and provenance]
    E --> H[Text answer and optional charts for human review]
    Z -->|Unresolved| W[Release eligible supported claims as partial; withhold the rest and charts]
```

## References used

For current shared rules, diagnostic/privacy contracts, dated run results and all other
guides, use the [documentation map](DOCUMENTATION_MAP.md). Classroom source-inspection
dates below are historical; this documentation review did not repeat an external review.

- Classroom `text2sql_example/text_to_sql.ipynb`: schema-aware questions, few-shot mappings and read-only results. Echo adds scoped data copies and SQLite authorization.
- Classroom `rag_example/rag_query.ipynb`: retrieval -> source context -> cited generation; semantic retrieval uses cosine similarity.
- Classroom `benchmark_example/mini_benchmark.ipynb`: fixed questions and independently held expected criteria. An offline fixture cannot substitute for its real model calls.
- Classroom `llm_as_judge_example/llm_as_judge.ipynb`: seven independent dimensions, rationales and uncertainty.
- Shared transcript `AI agents explained_ Build your first agent in 8 minutes.txt`, 03:25–06:45: explicit specialist instructions, shared results, separate checkers and bounded retries. This supports the dedicated Lime role; Echo does not require ADK.
- Shared transcript `Local AI Agents In 26 Minutes.txt`: local tools, configurable models, restricted capabilities and traces. Local execution does not imply offline model inference.
- [Anthropic agent architecture](https://www.anthropic.com/engineering/building-effective-agents): composable specialist and evaluator workflows. The additional role is justified here by its separate chart-selection responsibility.
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling): schemas, model tool calls, application execution and tool-result messages. A schema is not a factual-correctness guarantee.
