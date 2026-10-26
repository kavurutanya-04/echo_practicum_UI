# Echo: five agents with interchangeable model connections

Echo's Python code, prompts, configuration and operating documentation are in English.
The local SQLite database is built from eleven application tables (630,339 synthetic rows
in the inspected dataset). A new clone runs `import_data.py` once; an existing database
does not need another import to configure a provider. Reviewed: 2026-10-23. See
[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for observed results and the
[reference map](DOCUMENTATION_MAP.md) for current guides and historical notes.

| Agent | Role | Access |
| --- | --- | --- |
| **Original** | Coordinate questions, delegate to specialists and combine evidence | Cherry/Vanilla tools; no direct SQL or file access |
| **Cherry** | Generate SQL from a question and explain numeric results | Restricted structured-data copy and read-only SQL |
| **Vanilla** | Retrieve cited themes and systematically classify scoped survey sentiment | Scoped surveys, feedback, contributions, work descriptions and priority explanations |
| **Lime** | Independently choose indicator charts and export accepted local SVG/CSV files | Supplied SQL evidence only; no database access or generated code |
| **ZeroSugar** | Review the candidate against evidence and request corrections | Evidence checks, structured seven-dimension model review; no unrestricted database access |

Original, Cherry, Vanilla and ZeroSugar retain their existing names; Lime is the fifth role. Engagement, recognition and priority conflicts are analysis topics across these roles. Detailed responsibilities, outputs, tools and worked examples are in [AGENT_ROLES.md](AGENT_ROLES.md).

The 2026-10-26 audit follow-up requires an assessment of every pending correction even
if ZeroSugar omits the assessment field. Responses requests/logs honor the configured
output limit, and budgeted Chat attempts recheck the existing deadline after waiting
and before sending. Provider settings and Echo_UI are unchanged. See the
[follow-up contract](WORKFLOW_RELIABILITY.md#audit-follow-up-review-coverage-output-limits-and-request-deadlines-2026-10-26)
and [focused offline checks](TESTING_AND_RAG.md).

The 2026-10-23 update simplifies Original's synthesis instructions and retires the mandatory
deliverable checklist. ZeroSugar first reviews visible-answer completeness without sources,
then separately reviews support with the evidence. Both stages participate in acceptance;
actual pending corrections survive revision, while optional wording stays a suggestion.
New finding reviews use block IDs and code retains their citations. Normal review adds
one model call per candidate within existing budgets. The 242-test offline agent suite
passed; real-model answer quality remains pending. See the [current workflow](WORKFLOW_RELIABILITY.md#autonomous-synthesis-and-two-stage-review-2026-10-23).

## Start with the correct kind of test

The [workflow reliability update](WORKFLOW_RELIABILITY.md) adds validated recurring metrics,
bounded closure, selective roles, localized repairs and independent finding review. Original
returns `complete`, `partial`, `needs_clarification` or `failed`; partial output contains only
independently supported blocks. All output is English. `--output` also preserves known
failures as explicitly failed artifacts, rather than silently omitting the file.
`verification.status` distinguishes a review that was `not_run`, `failed`, or `completed`;
the terminal no longer presents an unexecuted review as a ZeroSugar revision verdict.
Interrupted specialists may retain evidence for independent review; preserved work is
not automatically published. See [repair and recovery](WORKFLOW_RELIABILITY.md#repair-feedback-and-retained-evidence-2026-10-21).

Every `run_agent.py` execution (including connection checks and runs launched by
`evaluate_live.py`) automatically creates a unique local `reports/logs/*.jsonl` log.
The terminal prints its absolute path at startup. Events are flushed as they happen,
so completed steps remain available after a failure or cancellation, even without
`--output`. Logs record UTC timestamps, roles, model calls, tool activity, validation
repairs and the final status. They exclude keys, environment values, prompts, answers,
raw provider errors and employee records. Logs stay local and are ignored by Git.
`--show-connections`, `--help` and argument parsing failures do not create execution logs.
The optional `--output` JSON remains the completed answer/evidence artifact; the live
evaluation review record also links to its execution log. A forced process stop can
leave a log ending at the last started step without a final status. Earlier failures
that had no log cannot be reconstructed retroactively.

Live evaluation is already in progress. Luna's fourth run completed a source-matching
numeric comparison; its tenth comment run reached completed reviews and released partial
findings but omitted requested literal examples from the visible answer. It predates the
coordination update. Preserve that artifact and use a fresh filename for a later authorized
attempt. Python runs Echo locally in both
modes: with a configured API it calls a real model; `--demo` substitutes programmed
responses. Connection probes establish API/tool access for that request, not analytic quality.

**Without configured API credentials, you cannot test a real model's reasoning.** Offline tests/demo validate engineering with scripted/mocked responses. Live mode requires a real provider and fails rather than silently simulating an answer. [TESTING_AND_RAG.md](TESTING_AND_RAG.md) explains secure configuration, a real connection probe, retrieval inspection and fixed live evaluations.

```powershell
python .\run_agent.py --show-connections
python .\run_agent.py --check-connection --profile google_test
```

The first command shows assignments only; it does not test connectivity. The second makes an actual minimal API call and requires the variables below. It never uses a fixture or supplies employee data.

## Run the full workflow now, without credentials

Open a terminal inside `Final_Project/Agent_Echo`, using Python 3.11 or newer:

```powershell
python .\run_agent.py original --manager M14 --demo --output .\reports\original_offline_demo.json
```

This executes the real scoped SQL tools, local text retrieval and evidence-bound SVG export. Model choices, final wording, chart selection and judge scores are scripted fixtures. It verifies integration, not LLM reasoning or answer quality. It does not read credentials or connect to a provider. `--question` is ignored in demo mode. The console and artifact explicitly report zero generation API calls.

The artifact stores the question, manager/date scope, specialist delegations, evidence, tool trace and verification history. The terminal explicitly labels offline verification as a fixture. Individual agent examples remain available:

```powershell
python .\run_agent.py cherry --manager M14 --demo --output .\reports\cherry_offline_demo.json
python .\run_agent.py vanilla --manager M14 --demo --output .\reports\vanilla_offline_demo.json
python .\run_agent.py zerosugar --manager M14 --demo --input .\reports\cherry_offline_demo.json --output .\reports\zerosugar_offline_demo.json
```

## Systematic survey sentiment

Vanilla's `analyze_survey_sentiment` classifies every eligible comment in the requested
scope/dimension, not the top search hits. Its model assigns positive/negative/neutral/
mixed/indeterminate labels; code computes percentages using all eligible comments in each
group and suppresses groups below five comments. Quotes copy contiguous response text
verbatim, up to 400 characters; explanations are separate, up to 160. Each 20-comment batch
has at most three attempts, repairing only pending records. Valid labels and attempt
counters survive same-workflow redelegation for identical source/scope/model inputs;
independent runs reset them. Exhaustion returns incomplete progress without percentages.

Saved JSON includes completed labels, source IDs, literal excerpts and source hashes.
Publishable examples also become individual canonical text evidence for Vanilla/Original
to cite and ZeroSugar to independently check. Counts from these labels belong to Vanilla,
not Cherry's SQL/rating metrics. The fifth live run completed a child classification but
never reached ZeroSugar or released an answer. Semantic label quality remains unmeasured;
`human_validated=false` is not changed by passing source/aggregation checks.

After configuring the API, run a bounded real evaluation:

```powershell
python .\evaluate_live.py --case survey_sentiment --profile google_test
```

For a larger corpus, `run_agent.py` accepts an explicit `--model-call-limit` (default 32, maximum 256) and `--run-seconds` (default 300, maximum 3600). Classification batches contain 20 comments; the tool checks required calls before starting and never publishes partial percentages. Lime continues to accept only Cherry's SQL evidence, so sentiment summaries are currently text/tables in the JSON artifact. Full contracts and limitations are in [AGENT_ROLES.md](AGENT_ROLES.md).

## One connection layer, selectable profiles per agent

`connections.json` is the single source of non-secret connection settings: provider, API type, explicit endpoint, model/deployment, API version, request limits and agent assignments. `.env` contains API keys only. `agents/connections.py` reads those settings and constructs clients; it has no model names or service addresses built into it.

**GW Azure remains the primary/final provider.** All five roles inherit `gw_azure` by default. Optional profiles are experiments, never automatic fallbacks. Unconfigured model/deployment or endpoint fields stay empty until you obtain real assigned values; Echo does not guess them.

| Profile | Provider/API | API key variable |
| --- | --- | --- |
| `gw_azure` | University Azure, Responses API | `GW_AZURE_OPENAI_KEY` |
| `google_test` | Gemini, compatible Chat Completions | `GOOGLE_API_KEY` |
| `personal_openai` | OpenAI, Responses API | `OPENAI_API_KEY` |
| `nvidia_test` | NVIDIA hosted Chat Completions; Nemotron 3.5 Super VL | `NVIDIA_API_KEY` |
| `nvidia_glm_test` | Z.AI GLM-5.3-Flash hosted by NVIDIA | `NVIDIA_API_KEY` |
| `opencode_test` | Connection reference; free external calls previously rejected | `OPENCODE_API_KEY` |
| `apinex_test` | APInex compatible Chat Completions; Luna for all roles when explicitly selected | `APINEX_API_KEY` |
| `gw_embeddings` | Azure embeddings | `GW_AZURE_OPENAI_KEY` |
| `google_embeddings` | Google embeddings | `GOOGLE_API_KEY` |
| `openai_embeddings` | OpenAI embeddings | `OPENAI_API_KEY` |

For every profile, edit `model` and `endpoint` directly in JSON. Azure legacy profiles also declare `api_version`; Azure v1 profiles must supply their complete API base URL, including `/openai/v1/`. Generation profiles declare `max_output_tokens`, `timeout_seconds` and `max_retries`; APInex additionally uses `request_interval_seconds` and `rate_limit_retries`, with SDK retries disabled. `key_env` names the credential variable; it never contains the key itself. The private file is ignored by Git. Real key values must never enter JSON, source code, examples or logs.

Selection precedence is explicit: `--profile` for the current run, then the role's JSON assignment, then JSON `default_profile`. Model, endpoint, API-version and role overrides from `.env` or terminal variables are no longer used. Legacy JSON fields `model_env`, `endpoint_env` and `api_version_env` are rejected with a migration message. Only API keys use environment precedence: the process environment first, then the private `.env`. The legacy `from_environment()` entry point also follows JSON profile selection.

Inspect the effective non-secret configuration without reading credentials:

```powershell
python .\run_agent.py --show-connections
python .\run_agent.py --show-connections --profile google_test
```

For mixed-model experiments, edit the `agents` object in `connections.json`, for example:

```json
{
  "Original": "nvidia_test",
  "Cherry": "nvidia_glm_test",
  "Vanilla": "google_test",
  "Lime": "nvidia_test",
  "ZeroSugar": "nvidia_glm_test"
}
```

Omit `--profile` to use those assignments. Supplying it forces the selected profile for every role. Roles share a stateless client for the same profile but keep their own instructions and histories. The connection probe tests each distinct selected profile once. These assignments are an experiment, not a quality ranking; each selected model must support tool calling.

## Primary final connection: GW Azure AI Foundry

Live output uses the [source-bound fact and claim contract](SOURCE_GROUNDING.md).
Models select recorded facts; Python renders numerical claims and tables, while text
interpretations remain explicitly provisional and subject to independent review.
Current answers use `source-facts-v3`: interpretations may cite text or source rows with
`quote=null`, regardless of source count; supplied examples keep literal excerpts. Digits
and quantifiers in narrative are review warnings, not automatic errors. Known citation
wrappers/inline references and whitespace are normalized. A selected source table is not
repeated as individual numeric-cell sentences. Original can revise presentation while
preserving facts/provenance. ZeroSugar's optional `suggestions` are separate from mandatory
`issues`. Saved v1/v2 answers remain reviewable through their original rendering contracts.
ZeroSugar receives warning context and available code-computed comparisons; its per-finding
reason must address semantic support rather than reject typography. Counts, source integrity
and scope remain code-checked. This does not guarantee a correct model review.

Use only your group's assigned Azure resource and deployment. In `connections.json`, fill `profiles.gw_azure.endpoint` and `profiles.gw_azure.model` with the actual resource URL and Responses-capable deployment name. The JSON `api_version` retains the professor's `2025-03-01-preview` setting. Configure the separate `gw_embeddings` endpoint and embedding deployment in JSON only if semantic retrieval is needed. Keep unavailable fields empty rather than inventing values.

Store only `GW_AZURE_OPENAI_KEY` in the private `.env` or process environment. The endpoint format for the legacy client is `https://YOUR-ASSIGNED-RESOURCE.openai.azure.com/`. Do not share the key or commit it. Echo validates the JSON connection before loading credentials and never falls back to a test provider when GW settings are missing.

```powershell
python .\run_agent.py --show-connections --profile gw_azure
python .\run_agent.py --check-connection --profile gw_azure
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile gw_azure --question "Review recognition using quarterly metrics and anonymous comments. Explain limitations."
```

## Test NVIDIA and OpenCode with private local keys

For the optional single-model APInex/Luna workflow, private key setup, pacing and verified access status, see [APInex SDK trial](TESTING_AND_RAG.md#apinex-sdk-trial). `--profile apinex_test` uses Luna for every role with a shared 20-second request interval, bounded HTTP 429 retries and a 6000-token output maximum.

Open the local `.env` in this directory and paste each key after its equals sign:

```dotenv
NVIDIA_API_KEY=
OPENCODE_API_KEY=
```

This file is excluded from Git and exists separately on each computer. GitHub includes `.env.example`, an empty-key template. A new collaborator creates their own `.env` by copying that template (only if `.env` does not already exist), then pastes their own key values into `.env`. The application reads it automatically when a live client needs a key. Never replace an existing `.env` while copying the template.

Do not put real keys in `connections.json` or `.env.example`. The private `.env` and process environment supply keys only; process keys take precedence. Model, endpoint, version and role settings come exclusively from JSON (or the explicit `--profile` selection). `--show-connections` and `--demo` do not read the private file. Unused profiles do not require keys, and offline demos need none.

With the `echo-agent` environment active and `requirements.txt` installed, test one provider at a time:

```powershell
python .\run_agent.py --check-connection --profile nvidia_test
python .\run_agent.py --check-connection --profile nvidia_glm_test
python .\run_agent.py --check-connection --profile opencode_test
```

Each command makes one minimal real tool call without employee data and prints a progress message to stderr while waiting. The NVIDIA profiles use `nvidia/nemotron-3.5-super-vl-120b-a12b` and `z-ai/glm-5.3-flash` at `https://integrate.api.nvidia.com/v1`. Both allow 8192 output tokens and a 120-second request timeout with no automatic retry. Other profiles retain 45 seconds and one retry unless explicitly configured. A profile can set `timeout_seconds` (greater than 0, at most 600) and `max_retries` (0-3). Workflow time/call limits still apply independently. OpenCode uses `deepseek-v4.1-flash-free` at `https://opencode.ai/inference/openai/v1`. The GLM profile retains NVIDIA's documented `reasoning_effort=low` and `clear_thinking=true`; a diagnostic can omit these settings in memory to compare behavior without changing the default. The adapter preserves provider reasoning fields needed during tool calls and distinguishes output-token exhaustion from HTTP failures. These profiles do not switch to paid models on failure. Check current availability, limits and retirement banners before testing. A free endpoint can be task-specific: Echo needs a chat model with function calling, not an arbitrary vision, pose or tabular endpoint.

**Live access findings, 2026-10-16:** OpenCode rejected external requests with HTTP 403 `FreeTierError`, stating that its free tier can only be used inside OpenCode. Its free default is therefore not usable for Echo's Python calls under that tested access; the profile remains a connection reference, not a verified free service. Bounded NVIDIA GLM probes timed out without an HTTP response, and a Nemotron Ultra probe returned HTTP 404 despite the model appearing in the catalog. NVIDIA's models-list endpoint responded, but additional short tool-call diagnostics for its DeepSeek V4.1 Flash and Nemotron 3.5 Lightning entries also timed out. These latter diagnostics did not add or select new default profiles. Those initial probes did not confirm NVIDIA tool-call access or analytic quality; the follow-up results below supersede that initial access status. The public catalog and earlier offline adapter tests do not override these observed results.

**Follow-up configuration, 2026-10-16:** The user reports a successful Nemotron Super text completion with 300 output tokens, while Ultra returned HTTP 404 "Function id ... is not found". The default trial model is therefore Super. This does not establish whether the Ultra failure was caused by account permissions or endpoint routing. HTTP 200 with no visible content at 20 tokens does not prove usable tool calling; reasoning can consume the output budget. Echo already used 8192 tokens in its earlier NVIDIA probes, so those 20-token experiments do not establish the cause of Echo's timeouts. Minimal tool-call and full analytic quality checks remain separate.

**Verified follow-up, 2026-10-16:** With the updated local key and 8192 output tokens, Nemotron Super passed Echo's real `connection_check` tool call. GLM-5.3-Flash passed both a separate plain probe with `reasoning_effort` and `clear_thinking` omitted in memory and the configured profile with `reasoning_effort=low` / `clear_thinking=true`. Both GLM probes took close to two minutes, so the reasoning options are not established as the cause of the earlier timeouts. The configured GLM defaults are retained; one successful probe does not guarantee future latency or availability. This establishes minimal tool access for these tested configurations; no full manager-answer or analytic-quality evaluation was performed. Logs and the probe summary stay under the ignored local `reports/` directory.

**Model update, 2026-10-20:** NVIDIA now marks the old Nemotron 3 Super free endpoint as deprecated. The `nvidia_test` profile now selects `nvidia/nemotron-3.5-super-vl-120b-a12b`, whose public page lists an available free endpoint and Python Chat Completions support. The successful October 16 tests above used the old model and do not validate this new model. Model selection now comes only from `connections.json`; legacy `.env` and terminal model overrides are not used. GW Azure remains the primary final provider. Current model reference: [Nemotron 3.5 Super VL](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b).

**New-model live check, 2026-10-20:** Echo's `--check-connection --profile nvidia_test` completed one real `connection_check` tool call with Nemotron 3.5 Super VL, shared across all five role assignments. This confirms API access and minimal tool calling, not manager-answer quality or token consumption. Local execution log: `reports/logs/20261020_213401_ec97b74226cb.jsonl`. All 19 provider-connection tests passed.

NVIDIA documents free hosted endpoints for prototyping, subject to service limits. It does not promise an unlimited request rate or production service. An NVIDIA staff forum response explains that limits vary by model, use case and current traffic; no account-specific quota was verified here. Use [NVIDIA's FAQ](https://docs.api.nvidia.com/nim/docs/product) and [NVIDIA's rate-limit explanation](https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-to-200-rpm-personal-agentic-ai-development/373359) rather than third-party quota estimates.

Failures now distinguish HTTP 401 (authentication), 403 (access restrictions), 404 (model/endpoint unavailable), 429 (quota), provider service errors, network failures and timeouts without echoing raw error payloads or keys. A Ctrl+C cancellation exits cleanly with status 130 rather than displaying a traceback. A timeout does not establish that a key is valid or invalid.

Sources: [NVIDIA model catalog](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b), [GLM-5.3-Flash capabilities and chat settings](https://docs.api.nvidia.com/nim/reference/z-ai-glm-5-3-flash), [GLM endpoint and model ID](https://docs.api.nvidia.com/nim/reference/z-ai-glm-5-3-flash-infer), [NVIDIA prototype terms](https://docs.api.nvidia.com/nim/docs/product), [OpenCode model pricing](https://opencode.ai/v2/docs/console/models/), [OpenCode inference API](https://opencode.ai/v2/docs/console/api/inference/). Checked 2026-10-16; availability remains account-dependent and tool-call confirmation does not establish analytic quality.

## Optional Google test and equivalent terminal setup for GW Azure

Activate the project environment and install dependencies:

```powershell
conda activate echo-agent
python -m pip install -r requirements.txt
```

Configure `profiles.google_test.model` and `endpoint` in `connections.json`. The migrated local Gemini model and NVIDIA model are preserved there. `.env.example` lists key names only and is not loaded automatically. If the key is not already in the private `.env`, enter it securely in the terminal:

```powershell
$env:GOOGLE_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Google API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile google_test
```

For GW Azure, configure the assigned endpoint and deployment in JSON first, then provide only the secret in the environment:

```powershell
$env:GW_AZURE_OPENAI_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "GW Azure API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile gw_azure
```

Changing a profile does not change prompts or data tools. Use identical cases and scopes for model comparisons. API access, correct tool use and analytic quality are separate checks.

## Lexical, semantic and hybrid RAG

The default is credential-free **lexical** retrieval with SQLite FTS5/BM25. Optional **semantic** retrieval embeds the question/passages and ranks cosine similarity, matching the professor's RAG approach. **Hybrid** combines semantic and lexical ranks. Scope/source/dimension filters precede top-k selection, and identical source passages are deduplicated.

Generation models and embedding models have separate profiles. To test hybrid RAG entirely with Google, first set `profiles.google_embeddings.model` in `connections.json` to a text embedding model available to your account, then run:

```powershell
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --retrieval hybrid --embedding-profile google_embeddings --question "What do recognition comments and quarterly metrics suggest?" --output .\reports\google_hybrid_review.json
```

For Azure, select `--profile gw_azure --retrieval hybrid --embedding-profile gw_embeddings` and configure the embedding deployment separately. Changing the generation profile does not silently change the embedding provider.

The first semantic/hybrid run sends scoped passage text to the selected embedding provider and creates a local vector cache in `data/rag_cache`. It can require many requests; start with one quarter. Subsequent runs reuse document vectors. Caches contain text hashes/vectors, and are separated by manager/date scope, provider/model/endpoint identity. Completed batches survive later request failures. The corpus stays local, but scoped text is sent to cloud inference/embedding APIs when configured; local execution is not offline inference.

Retrieved passages are examples, not a representative sentiment sample. Similarity scores are not confidence or prevalence. No percentages, causal improvement claims or employee identification may be inferred from ranked comments.

## Coordination and verification

Lime is the dedicated visualization role, named consistently with the project's Coca-Cola flavors. Its model receives only Cherry-produced SQL evidence as data, plus the question/candidate answer for context. Query results now identify `producer=Cherry`; other agents' numeric data, raw passages and retrieval scores are excluded. The former `visualizer` CLI name remains an alias for `lime`. Re-run Original for an older saved artifact lacking producer metadata before re-planning its charts.

Original uses Cherry/Vanilla as tools, following the classroom root/agent-tool pattern.
Its plan selects SQL metrics, text/sentiment and optional charts separately. Lime runs
only when a chart is planned; its model chooses indicator/type/axes from Cherry's evidence.
Cherry, Vanilla and Lime can return a structured decline for incompatible tasks in an
existing turn. Original can correct the assignment without resending an identical closed
request. Missing evidence, incomplete classification and execution failure are distinct
outcomes. ZeroSugar reviews claims, task coverage and any chart plan, combining source
checks with its seven-dimension model review; it does not author the candidate answer.

Only accepted plans are exported by `LimeAgent.export` / `agents/chart_export.py` as local SVG graphics, exact selected CSV columns and JSON provenance. Bars compare categories; lines show dates/quarters; nulls remain missing. No model-generated numbers, arbitrary code or web frontend are involved. SVG graphics are local output artifacts, not a dashboard. ZeroSugar reviews structured specs/data, not rendered pixels; human layout inspection remains separate.

To re-plan charts for an accepted saved Original result, use `python .\run_agent.py lime --manager M14 --input .\reports\live_review.json --profile google_test --output .\reports\visual_review.json`. The new plan is reviewed against the scoped source before export. Live mode refuses scripted artifacts. Use `--demo` only for an explicitly labeled fixture artifact. `--charts-dir` optionally selects the local export directory.

Vanilla records retrieval method, query/filter metadata, returned source IDs and cited IDs in `rag`. Source passages reach the next generation call as function-tool results. Original records these traces under `rag.specialist_runs`. This establishes the retrieval/context path, not claim correctness; live grounded reasoning still needs API calls and independent review. `inspect_rag.py` inspects retrieval alone; `evaluate_live.py` runs fixed live cases without giving expected criteria to agents.

Deterministic issues force revision even if the model accepts. The coordinator gets one revision opportunity. A twice-rejected draft is retained in the local trace but withheld from the user-facing answer. Global limits cover model calls, tools, embeddings and elapsed time, with additional per-agent and SQL limits. These are bounded execution controls, not a guarantee of claim correctness. Human review remains necessary.

Direct Cherry/Vanilla runs are specialist diagnostics and do not automatically invoke ZeroSugar. Use Original for the verified workflow, or review a saved artifact separately. Standalone ZeroSugar also reloads the scoped source data for SQL/text integrity checks. CLI exit codes are 0 for completion, 1 for execution/configuration failure, and 2 for partial results, clarification, declined/incomplete tasks or required revision. Cancellation is 130. A decline never exports charts or represents an approved analysis.

## Data access

The trusted backend opens `data/echo.db` read-only and selects the manager's pilot roster/date scope before the model sees data. Cherry queries a separate in-memory copy of permitted fields. It cannot access source/system tables, attach databases, change records or load extensions. Survey tokens/contact email/private QA datasets and raw feedback text are excluded. Individual program-use histories become team aggregates with at least five employees.

Vanilla receives only authorized textual records. Surveys are anonymous team records with at least five responses; other narrative records belong to the selected manager's employees. Feedback authors can come from partner teams. Every passage retains its source, ID, team and date. Model text cannot change the scope.

A CLI manager selection is a demo filter, **not authentication**. A deployed interface must build `AccessScope` from authenticated caller permissions. The dataset's pilot manager/team mapping is not a history of reporting-line changes. Named operational records support contribution review; anonymous surveys cannot be linked to individuals. Synthetic data cannot establish real business impact, and missing recognition notes do not prove that recognition never happened.

Cherry's temporary tables are `employees`, `survey_summary`, `program_summary`, `recognition_feedback`, `projects`, `work_requests`, `capacity`, `priority_decisions`, and `contributions`. These are access copies, not new CSVs or changes to the eleven application tables.

## Validation and project files

```powershell
python -m unittest discover -s tests -v
```

The latest implementation check passed **207 offline tests on 2026-10-21**, including
22 new sentiment workflow regressions. Coverage includes source reconciliation, scope,
provider/message contracts, pacing, shared policies, bounded clarification and repairs,
claim rendering, minimized rejection diagnostics, canonical comments, full sentiment
coverage and Original -> Vanilla -> ZeroSugar integration. These were scripted engineering
checks with zero generation API calls, not classifier accuracy measurements. This later
documentation-only review checked content/links; it did not rerun live or offline models.

[REFERENCE_VALIDATION.md](REFERENCE_VALIDATION.md) records the exact classroom materials reviewed, differences, fixes and remaining live validation. `tests/evaluation_cases.json` contains fixed live questions and independent review criteria; it is excluded from agent retrieval. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) preserves classroom attribution.

`agents/original.py`, `cherry.py`, `vanilla.py`, `lime.py` and `zero_sugar.py` define the five roles. Shared runtime/connections, scoped tools, semantic retrieval and the SVG exporter are supporting infrastructure. `run_agent.py` is the terminal entry point. No Google ADK or plotting-package installation is required for this provider-independent implementation.

`agents/policies.py` supplies six common rules to all analysis call paths. Role modules
retain their specialized duties; `AGENTS.md` guides coding work and is not loaded into
Echo model calls. Minimized rejection diagnostics omit raw rejected prose/quotes and
credentials, but normal local evidence artifacts can contain authorized source text.
Planning and v3 answer diagnostics are targeted exceptions: rejected/normalized clarification
fields and rejected narrative items retain bounded redacted context and feedback in JSONL
and result diagnostics. `answer_normalizations` records presentation repair; `review_warnings`
records narrative signals and ZeroSugar's assessment. Recognizable private identifiers are
redacted, with no guarantee of detecting every personal detail. Full prompts/provider payloads
are not added. See [planning diagnostics](WORKFLOW_RELIABILITY.md#planning-normalization-and-diagnostics-2026-10-21)
and [v3 review signals](WORKFLOW_RELIABILITY.md#narrative-review-signals-and-presentation-v3-2026-10-21).

## Existing data utilities

`import_data.py` imports the eleven approved CSVs from adjacent `files_update`, validates row counts/keys/integrity and excludes private QA files. The database already exists. Rebuild it only after source changes with `python .\import_data.py --replace`; source CSVs are preserved.

`recognition_report.py` remains a fixed-query utility, separate from the agents. Example: `python .\recognition_report.py --manager M14 --quarter 2026-Q3`. It produces an English report and explains synthetic recognition-note limits.
