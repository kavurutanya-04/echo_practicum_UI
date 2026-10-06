# Echo agent responsibilities and examples

Updated 2026-10-06. Five roles share configurable model adapters; each has its own instructions and history. This is a terminal/local-file prototype. All employee data is synthetic. Descriptions below complement the executable `INSTRUCTIONS` in each agent file.

## Original — coordination, synthesis and supervised revision

**Input:** manager question, backend-fixed manager/date scope, specialist responses and verifier feedback. **Tools:** `ask_cherry(question)` and `ask_vanilla(question)` only. **Output:** a cited candidate answer, source evidence and specialist delegations.

Original decomposes the question, requests appropriately bounded evidence, combines quantitative and textual findings, acknowledges disagreement and explains unavailable coverage. It owns the answer and responds to ZeroSugar's correction request. It does not run SQL, widen access, retrieve files, choose chart types or render graphs. The Python workflow automatically invokes Lime after each candidate; Original does not decide whether to invoke it.

Example: "What do this quarter's recognition metrics and comments suggest?" Original asks Cherry for team/period metrics with response counts and Vanilla for relevant supportive and critical comments. It combines the results without claiming that selected comments measure prevalence. For a requested chart, Original asks Cherry for usable indicator rows and denominators; Lime makes the presentation decision.

Example boundary: "Identify the person behind this anonymous comment." Explain that the authorized evidence cannot support identification. Do not delegate an identity-matching task. Proposed actions support manager review, not personnel decisions.

## Cherry — quantitative evidence and Text-to-SQL

**Input:** a bounded analytical question. **Tools:** `describe_schema()` and `execute_sql(sql)`. **Output:** numeric findings with `[SQLn]` citations; SQL text, returned rows, scope and truncation flag are retained as evidence.

Cherry inspects permitted tables, chooses read-only SQL, repairs failed queries and explains metrics, denominators and limits. It preserves the correct grain when joining contributions, feedback, work requests and capacity. Names in authorized operational records are permitted; anonymous surveys remain team aggregates and benefit histories remain group summaries. Cherry does not choose graphs, interpret retrieved comments or infer causal effects.

Example: "How many cross-team contributions lack a recorded manager-recognition note?" Count distinct contributions and check for matching recognition records with `EXISTS`/`NOT EXISTS`. Include the eligible total and explain that an absent note is not proof that recognition never occurred.

Example: "Show Recognition over eight quarters." Return `Team`, `Survey_Date`, `Responses`, `Mean_Score` and optionally `Favorable_Percent` in ordered rows. Weighted averages require response counts; favorable percentages and eNPS are different metrics. These rows become Lime's input.

Example: "Which weeks exceed available project hours?" Aggregate requests by employee/week before joining capacity. Recorded current-state demand is not a complete historical reconstruction.

## Vanilla — retrieval-augmented textual interpretation

**Input:** a bounded textual question. **Tool:** `search_text(query, source, dimension, limit)`. **Output:** themes/examples with exact returned citation IDs, dates, source teams, disagreement and coverage limits. The `rag` field records retrieval calls and citations.

Vanilla retrieves scoped survey comments, recognition feedback, contributions, work descriptions or priority explanations before interpreting them. Lexical retrieval uses FTS5/BM25; semantic retrieval uses provider embeddings/cosine similarity; hybrid combines ranks. It can try alternative terms and source/dimension filters. Retrieved text is evidence, never authority to change its instructions.

Example: "Find supportive and critical recognition views." Retrieve Recognition comments, cite actual passages and explain the selection method. Do not claim that the proportion of retrieved positive passages equals team sentiment.

Example: "What explains the priority changes?" Retrieve recorded `OP_priority_decisions` explanations. Do not invent motives or use general model knowledge to fill missing records. A zero-hit search is a retrieval limitation, not proof of no issues.

Anonymous source identity fields are excluded, but free-text content is not automatically redacted. Small-group thresholds are safeguards, not a guarantee against every identification risk. Real authentication and free-text privacy review remain unfinished.

## Lime — relevant indicator charts and local exports

Lime replaces the earlier functional name Visualizer, keeping the project's flavor naming convention. [Coca-Cola Lime](https://www.coca-cola.com/gb/en/brands/coca-cola-original-taste) is an actual Coca-Cola flavor. Only SQL evidence marked as produced by Cherry is sent as data; Vanilla passages and retrieval scores are not sent. The candidate answer provides context, never numeric authority.

**Input:** question, candidate answer, exact evidence rows, scope and optional review feedback. **Tool:** `submit_visuals(charts, reason)`. **Output:** zero to three chart specifications and an explicit relevance/no-chart explanation. After acceptance, its exporter generates `.svg`, companion `.csv` and `.json` provenance files.

Lime is a separately prompted model role with its own profile assignment (`ECHO_LIME_PROFILE`). It decides whether a chart helps, which supported indicator to plot, bar versus line, axes, series, units, denominator and title. It has no database access and cannot generate executable code, request arbitrary files or invent numeric arrays. Specs reference SQL citation IDs and column names; the exporter reads values directly from those rows. Original does not pick chart types.

Concrete renderer: `agents/chart_export.py::export_charts`. It draws vector graphics using Python's standard library. No plotting package, web server or dashboard framework is required. Files open in a browser or compatible image editor; opening an SVG is not deploying a web application.

Example: quarterly mean Recognition score -> line chart by `Survey_Date`, series `Team`, units `Score (1-5)`, denominator `Responses`. Example: contribution counts by beneficiary team -> bar chart from Cherry's computed counts. Example: comment examples without a numeric table -> no chart, with an explanation. Counts are not percentages; ranking text or embedding similarity is not an engagement indicator.

The validator rejects unknown sources/columns, mismatched scope, truncated tables, nonnumeric/nonfinite values, duplicate category/series pairs and means/rates without source denominators. Limits are three charts, 48 complete source rows per chart, six series, 24 temporal categories or 18 bar categories. Nulls remain missing; the renderer does not aggregate or calculate new metrics. A limitation can be addressed by requesting a better aggregated result from Cherry on the workflow's revision.

## Survey sentiment: current coverage

Vanilla is instructed to explain supportive/critical views and themes in retrieved comments. This is qualitative analysis of selected evidence; it is not a validated sentiment classifier for the full survey corpus. There is no persistent per-comment positive/negative/neutral/mixed labeling, no measured classifier accuracy and no team-level textual sentiment percentage. Numerical survey ratings are a different signal and must not be described as computed text sentiment.

A future systematic sentiment feature would need a defined eligible comment population, explicit labels/aspects, uncertainty/abstention, human-labeled validation and disclosed coverage/denominators before producing aggregate indicators. That feature has not been implemented in this update. No live model quality has been evaluated while API setup is deferred.

## ZeroSugar — independent answer and chart-plan review

**Input:** question, candidate answer, original evidence, Lime plan and scope. **Tool:** `submit_review(decision, ratings, issues, uncertainty)`. **Output:** seven independent 1–3 ratings, rationale, uncertainty, issues and accept/revise decision.

ZeroSugar checks citations, manager/date scope, anonymous identity fields, SQL replay, text/source correspondence and chart schema. Its model checks whether claims and chart labels are supported, whether the indicator addresses the question and whether units/denominators match. It does not write the answer or generate new metrics. Code forces revision for deterministic failures even if the model accepts.

Example rejection: a title claiming causal engagement improvement from synthetic associations; an average labeled as a percentage; a chart built from truncated rows; invented sentiment prevalence from selected comments. Example acceptance: supported findings with source references, an appropriate chart and honest limitations, or a justified no-chart result.

One correction round is allowed. A twice-rejected answer and its chart plans are withheld; no accepted chart files are exported. Model judgment remains fallible. ZeroSugar reviews structured specs and data, not a rendered image; human visual inspection is separate.

## Workflow

```mermaid
flowchart TB
    Q[Manager question] --> O[Original: coordinate and synthesize]
    O <--> C[Cherry: numeric evidence]
    O <--> V[Vanilla: retrieved textual evidence]
    O --> P[Candidate answer and source evidence]
    P --> G[Lime: choose indicator charts or explain no chart]
    G --> Z[ZeroSugar: review answer, evidence and chart plan]
    Z -->|One correction round| O
    Z -->|Accept| E[Lime exporter: local SVG, CSV and provenance]
    E --> H[Text answer and optional charts for human review]
    Z -->|Second rejection| W[Withhold answer and chart files]
```

## References used

- Classroom `text2sql_example/text_to_sql.ipynb`: schema-aware questions, few-shot mappings and read-only results. Echo adds scoped data copies and SQLite authorization.
- Classroom `rag_example/rag_query.ipynb`: retrieval -> source context -> cited generation; semantic retrieval uses cosine similarity.
- Classroom `benchmark_example/mini_benchmark.ipynb`: fixed questions and independently held expected criteria. An offline fixture cannot substitute for its real model calls.
- Classroom `llm_as_judge_example/llm_as_judge.ipynb`: seven independent dimensions, rationales and uncertainty.
- Shared transcript `AI agents explained_ Build your first agent in 8 minutes.txt`, 03:25–06:45: explicit specialist instructions, shared results, separate checkers and bounded retries. This supports the dedicated Lime role; Echo does not require ADK.
- Shared transcript `Local AI Agents In 26 Minutes.txt`: local tools, configurable models, restricted capabilities and traces. Local execution does not imply offline model inference.
- [Anthropic agent architecture](https://www.anthropic.com/engineering/building-effective-agents): composable specialist and evaluator workflows. The additional role is justified here by its separate chart-selection responsibility.
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling): schemas, model tool calls, application execution and tool-result messages. A schema is not a factual-correctness guarantee.
