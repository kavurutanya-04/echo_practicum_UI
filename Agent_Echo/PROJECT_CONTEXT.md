# Echo: current project context

Reviewed: 2026-10-21 (America/New_York). This is a short entry point for future chats. It describes the local files inspected on this date; verify relevant sources before changing behavior. It is not a benchmark report or a transcript of every project conversation.

## Purpose and architecture

Echo is the Practicum HR/people-analytics prototype. It uses synthetic employee data to support manager review. The current application runs in a terminal and exports local artifacts.

| Role | Current responsibility | Main implementation |
| --- | --- | --- |
| Original | Plan the analysis, select specialists, combine evidence, and coordinate corrections. | [original.py](agents/original.py) |
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
| Diagnostics and release | Minimized answer/batch rejections preserve condition, field/index, source IDs and attempt metadata without rejected prose/quotes or keys. Authorized source text remains in local evidence. ZeroSugar reviews claims; incomplete work cannot be labeled complete, and only eligible supported claims can be partial. | [Diagnostics](WORKFLOW_RELIABILITY.md#rejected-source-answer-diagnostics-2026-10-21), [CLI guide](README.md) |

The latest implementation check passed **207 offline tests on 2026-10-21**, including
22 [sentiment workflow regressions](tests/test_sentiment_workflow_repairs.py), without
provider requests. Scripted labels test contracts, not model quality. The current
documentation review did not rerun that suite. Live confirmation of the fifth-run repairs
and independently measured sentiment quality remain pending.

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

These files are ignored local artifacts and may be absent in another checkout. Their metadata was checked; this documentation task did not rerun them or certify the findings. Do not describe all live evaluation as unstarted. A comparative winner remains unestablished.

Offline historical audit: four local artifacts, 13 role executions across Original/Cherry/Vanilla, zero API calls; source review packet at `reports/grounding_audit_before_upgrade.json`. No complete classification labels were preserved in those files, so semantic classifier accuracy is unavailable. Human query/entailment review remains pending; no old narrative result was retroactively certified.

For testing instructions, use [TESTING_AND_RAG.md](TESTING_AND_RAG.md). Run commands from `Agent_Echo/` with the project's Python environment:

```powershell
python -m unittest discover -s tests
python run_agent.py --show-connections
python evaluate_live.py --list
```

The latter two list configuration/cases without making model requests. Live evaluations require an explicitly selected case and configured provider access. Reports and incremental execution logs are local evidence; inspect them before reporting outcomes.

## Decisions, proposals, and pending work

- Immediate next step: repeat run five's exact Recognition-comment question and M14/Q3
  2026 scope with `--profile apinex_test --run-seconds 1000`, saving
  `reports/apinex_prueba_vanilla_6.json`. No saved sixth-run result was present at this
  documentation review. The [complete terminal command](TESTING_AND_RAG.md#next-live-test-sixth-luna-run)
  does not establish that a run was executed. Inspect actual citations, retained retries,
  task routing, ZeroSugar review, minimized diagnostics and gateway token/quota usage.

- Preserve the five-role baseline while evaluating answer quality, usefulness, and provider/model fit.
- The user wants evidence-grounded conclusions and useful partial results when independent findings survive a component failure.
- UI and enterprise integration are deferred in the existing decision document. Dedicated recommendation/planning/execution/monitoring roles are proposals, not implemented agents.
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
