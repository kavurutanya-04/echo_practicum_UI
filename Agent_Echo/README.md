# Echo: five agents with interchangeable model connections

Echo's Python code, prompts, configuration and project documentation are in English. Its existing SQLite database contains eleven application tables and 630,339 synthetic rows; it does not need another CSV import.

| Agent | Role | Access |
| --- | --- | --- |
| **Original** | Coordinate questions, delegate to specialists and combine evidence | Cherry/Vanilla tools; no direct SQL or file access |
| **Cherry** | Generate SQL from a question and explain numeric results | Restricted structured-data copy and read-only SQL |
| **Vanilla** | Retrieve cited themes and systematically classify scoped survey sentiment | Scoped surveys, feedback, contributions, work descriptions and priority explanations |
| **Lime** | Independently choose indicator charts and export accepted local SVG/CSV files | Supplied SQL evidence only; no database access or generated code |
| **ZeroSugar** | Review the candidate against evidence and request corrections | Evidence checks, structured seven-dimension model review; no unrestricted database access |

Original, Cherry, Vanilla and ZeroSugar retain their existing names; Lime is the fifth role. Engagement, recognition and priority conflicts are analysis topics across these roles. Detailed responsibilities, outputs, tools and worked examples are in [AGENT_ROLES.md](AGENT_ROLES.md).

## Start with the correct kind of test

The next product milestone is **live evaluation of the agents' reasoning**, not another scripted demo. Python runs Echo locally in both modes: with a configured API it calls a real model; `--demo` substitutes programmed responses. Local execution does not mean that inference is offline. API setup remains deferred at the user's request; no live quality result is available yet.

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

Vanilla's `analyze_survey_sentiment` classifies every eligible comment in the requested scope/dimension, not the top search hits. It uses the configured model for positive/negative/neutral/mixed/indeterminate labels; code computes percentages with all comments as the denominator and suppresses groups below five comments. Saved JSON includes labels, source IDs, supporting excerpts and source hashes. ZeroSugar rechecks coverage/provenance/aggregation. Labels are provisional pending human evaluation; no live classification has been run while API setup is deferred.

After configuring the API, run a bounded real evaluation:

```powershell
python .\evaluate_live.py --case survey_sentiment --profile google_test
```

For a larger corpus, `run_agent.py` accepts an explicit `--model-call-limit` (default 32, maximum 256) and `--run-seconds` (default 300, maximum 3600). Classification batches contain 20 comments; the tool checks required calls before starting and never publishes partial percentages. Lime continues to accept only Cherry's SQL evidence, so sentiment summaries are currently text/tables in the JSON artifact. Full contracts and limitations are in [AGENT_ROLES.md](AGENT_ROLES.md).

## One connection layer, selectable profiles per agent

`connections.json` lists profiles and each agent's optional profile assignment. It contains environment-variable names, never keys. All five roles inherit `gw_azure` by default. Roles using the same profile share one stateless client/adapter; their instructions and histories stay separate. One credential can serve all five agents on the same account/profile.

| Profile | Provider/API | Required environment variables |
| --- | --- | --- |
| `gw_azure` | University Azure, Responses API | `GW_AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` |
| `google_test` | Gemini, OpenAI-compatible Chat Completions | `GOOGLE_API_KEY`, `GOOGLE_MODEL` |
| `personal_openai` | OpenAI, Responses API | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `gw_embeddings` | Azure embeddings | GW key/endpoint plus `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` |
| `google_embeddings` | Google embeddings | Google key plus `GOOGLE_EMBEDDING_MODEL` |
| `openai_embeddings` | OpenAI embeddings | OpenAI key plus `OPENAI_EMBEDDING_MODEL` |

Show the selected profiles and variable names without reading key values:

```powershell
python .\run_agent.py --show-connections
python .\run_agent.py --show-connections --profile google_test
```

Selection precedence: `--profile` forces every model role in that run; otherwise a role-specific environment override wins over its JSON assignment, followed by `ECHO_DEFAULT_PROFILE`, then the JSON default. For a mixed-provider run, set `ECHO_CHERRY_PROFILE`, `ECHO_VANILLA_PROFILE`, `ECHO_ORIGINAL_PROFILE`, `ECHO_LIME_PROFILE`, or `ECHO_ZEROSUGAR_PROFILE`, or edit the corresponding non-secret JSON assignment.

Each selected model must support function calling. Deployment/model names are chosen from the account's actual access; they are not hardcoded. The professor's AzureOpenAI/Responses API version is retained by default. An Azure profile can set `azure_api` to `v1` to use the current Microsoft v1 client pattern when the assigned resource supports it. Credentials are never printed or written into artifacts. There is no automatic provider fallback.

## Test with Google, then switch to GW Azure

Activate the project environment and install the SDK if needed:

```powershell
conda activate echo-agent
python -m pip install -r requirements.txt
```

The example file `.env.example` lists variable names; the application does not automatically load it. Set variables in the same terminal session or through approved secret management. For a Google test:

```powershell
$env:GOOGLE_MODEL = "YOUR-TOOL-CAPABLE-GEMINI-MODEL"
$env:GOOGLE_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Google API key" -AsSecureString)).Password
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --question "Review cross-team recognition using counts and anonymous comments. Explain limitations." --output .\reports\google_review.json
```

When the university credential and assigned resource are available:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-ASSIGNED-RESOURCE.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "YOUR-RESPONSES-CAPABLE-DEPLOYMENT"
$env:GW_AZURE_OPENAI_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "GW Azure API key" -AsSecureString)).Password
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile gw_azure --question "Review cross-team recognition using counts and anonymous comments. Explain limitations." --output .\reports\azure_review.json
```

Changing the profile does not change agent prompts or data tools. Use identical cases/scopes for comparisons. Connection/deployment availability, live Text-to-SQL quality, Gemini tool handling and judge reliability have not been tested against a real provider in this implementation review.

## Lexical, semantic and hybrid RAG

The default is credential-free **lexical** retrieval with SQLite FTS5/BM25. Optional **semantic** retrieval embeds the question/passages and ranks cosine similarity, matching the professor's RAG approach. **Hybrid** combines semantic and lexical ranks. Scope/source/dimension filters precede top-k selection, and identical source passages are deduplicated.

Generation models and embedding models have separate profiles. To test hybrid RAG entirely with Google, first set `GOOGLE_EMBEDDING_MODEL` to a text embedding model available to your account, then run:

```powershell
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --retrieval hybrid --embedding-profile google_embeddings --question "What do recognition comments and quarterly metrics suggest?" --output .\reports\google_hybrid_review.json
```

For Azure, select `--profile gw_azure --retrieval hybrid --embedding-profile gw_embeddings` and configure the embedding deployment separately. Changing the generation profile does not silently change the embedding provider.

The first semantic/hybrid run sends scoped passage text to the selected embedding provider and creates a local vector cache in `data/rag_cache`. It can require many requests; start with one quarter. Subsequent runs reuse document vectors. Caches contain text hashes/vectors, and are separated by manager/date scope, provider/model/endpoint identity. Completed batches survive later request failures. The corpus stays local, but scoped text is sent to cloud inference/embedding APIs when configured; local execution is not offline inference.

Retrieved passages are examples, not a representative sentiment sample. Similarity scores are not confidence or prevalence. No percentages, causal improvement claims or employee identification may be inferred from ranked comments.

## Coordination and verification

Lime is the dedicated visualization role, named consistently with the project's Coca-Cola flavors. Its model receives only Cherry-produced SQL evidence as data, plus the question/candidate answer for context. Query results now identify `producer=Cherry`; other agents' numeric data, raw passages and retrieval scores are excluded. The former `visualizer` CLI name remains an alias for `lime`. Re-run Original for an older saved artifact lacking producer metadata before re-planning its charts.

Original uses Cherry/Vanilla as tools, following the classroom root/agent-tool pattern. Every candidate then goes to the separately prompted Lime, which chooses relevant indicator charts or explains why none is supported. Original does not decide chart type or rendering. ZeroSugar reviews both the candidate and chart plan. It checks citation IDs, dates/scope, anonymous fields, SQL replay, source-text correspondence and chart references/columns, then asks its configured model to judge Accuracy, Relevance, Completeness, Clarity, Instruction Following, Usefulness, and Safety / Appropriateness on a 1-3 scale.

Only accepted plans are exported by `LimeAgent.export` / `agents/chart_export.py` as local SVG graphics, exact selected CSV columns and JSON provenance. Bars compare categories; lines show dates/quarters; nulls remain missing. No model-generated numbers, arbitrary code or web frontend are involved. SVG graphics are local output artifacts, not a dashboard. ZeroSugar reviews structured specs/data, not rendered pixels; human layout inspection remains separate.

To re-plan charts for an accepted saved Original result, use `python .\run_agent.py lime --manager M14 --input .\reports\live_review.json --profile google_test --output .\reports\visual_review.json`. The new plan is reviewed against the scoped source before export. Live mode refuses scripted artifacts. Use `--demo` only for an explicitly labeled fixture artifact. `--charts-dir` optionally selects the local export directory.

Vanilla records retrieval method, query/filter metadata, returned source IDs and cited IDs in `rag`. Source passages reach the next generation call as function-tool results. Original records these traces under `rag.specialist_runs`. This establishes the retrieval/context path, not claim correctness; live grounded reasoning still needs API calls and independent review. `inspect_rag.py` inspects retrieval alone; `evaluate_live.py` runs fixed live cases without giving expected criteria to agents.

Deterministic issues force revision even if the model accepts. The coordinator gets one revision opportunity. A twice-rejected draft is retained in the local trace but withheld from the user-facing answer. Global limits cover model calls, tools, embeddings and elapsed time, with additional per-agent and SQL limits. These are bounded execution controls, not a guarantee of claim correctness. Human review remains necessary.

Direct Cherry/Vanilla runs are specialist diagnostics and do not automatically invoke ZeroSugar. Use Original for the verified workflow, or review a saved artifact separately. Standalone ZeroSugar also reloads the scoped source data for SQL/text integrity checks. CLI exit codes are 0 for completion, 1 for execution/configuration failure, and 2 when verification requests revision.

## Data access

The trusted backend opens `data/echo.db` read-only and selects the manager's pilot roster/date scope before the model sees data. Cherry queries a separate in-memory copy of permitted fields. It cannot access source/system tables, attach databases, change records or load extensions. Survey tokens/contact email/private QA datasets and raw feedback text are excluded. Individual program-use histories become team aggregates with at least five employees.

Vanilla receives only authorized textual records. Surveys are anonymous team records with at least five responses; other narrative records belong to the selected manager's employees. Feedback authors can come from partner teams. Every passage retains its source, ID, team and date. Model text cannot change the scope.

A CLI manager selection is a demo filter, **not authentication**. A deployed interface must build `AccessScope` from authenticated caller permissions. The dataset's pilot manager/team mapping is not a history of reporting-line changes. Named operational records support contribution review; anonymous surveys cannot be linked to individuals. Synthetic data cannot establish real business impact, and missing recognition notes do not prove that recognition never happened.

Cherry's temporary tables are `employees`, `survey_summary`, `program_summary`, `recognition_feedback`, `projects`, `work_requests`, `capacity`, `priority_decisions`, and `contributions`. These are access copies, not new CSVs or changes to the eleven application tables.

## Validation and project files

```powershell
python -m unittest discover -s tests -v
```

All **61 offline tests pass** as of 2026-10-06, including numeric reconciliation, scope controls, provider/message contracts, semantic vector/cache behavior, altered evidence, mandatory review, bounded revision/withholding, source database integrity, exact chart rows/missing values, invalid chart rejection, retrieval context reaching generation, missing-API failures and complete sentiment coverage/provenance/aggregation. Mocks do not establish live provider compatibility, chart-choice quality, sentiment accuracy or answer accuracy.

[REFERENCE_VALIDATION.md](REFERENCE_VALIDATION.md) records the exact classroom materials reviewed, differences, fixes and remaining live validation. `tests/evaluation_cases.json` contains fixed live questions and independent review criteria; it is excluded from agent retrieval. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) preserves classroom attribution.

`agents/original.py`, `cherry.py`, `vanilla.py`, `lime.py` and `zero_sugar.py` define the five roles. Shared runtime/connections, scoped tools, semantic retrieval and the SVG exporter are supporting infrastructure. `run_agent.py` is the terminal entry point. No Google ADK or plotting-package installation is required for this provider-independent implementation.

## Existing data utilities

`import_data.py` imports the eleven approved CSVs from adjacent `files_update`, validates row counts/keys/integrity and excludes private QA files. The database already exists. Rebuild it only after source changes with `python .\import_data.py --replace`; source CSVs are preserved.

`recognition_report.py` remains a fixed-query utility, separate from the agents. Example: `python .\recognition_report.py --manager M14 --quarter 2026-Q3`. It produces an English report and explains synthetic recognition-note limits.
