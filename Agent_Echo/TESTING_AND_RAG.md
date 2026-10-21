# What can be tested without an API, and how to verify RAG

Updated 2026-10-20. Run commands inside `Final_Project/Agent_Echo` with the project's Python environment. `.env.example` is a reference; live clients load only keys from the private, Git-ignored `.env` or process environment. Models, endpoints, API versions, limits and role selection are in `connections.json`; `--profile` is an explicit per-run selection. Never put real keys in files committed to Git. GW Azure is the primary/final provider; all other profiles are optional tests.

## Three different activities

For evaluating intelligence, use the live evaluation cases after configuring a provider. Running Python locally can still call a cloud LLM; the decisive distinction is live API responses versus programmed fixtures. The demo is an optional engineering diagnostic, not a reasoning benchmark. Provider access and analytic quality require separate checks; see the NVIDIA/OpenCode access findings below.

| Activity | Calls an API? | What the result establishes |
| --- | --- | --- |
| Unit/integration tests and `--demo` | No; scripted/mocked responses | Queries, restrictions, retrieval plumbing, rendering, review gates and error handling work on those cases. It does not evaluate LLM reasoning, chart selection or answer quality. |
| `inspect_rag.py --retrieval lexical` | No | Real local passages can be retrieved with source IDs and scope. No generated answer is produced. |
| Live agents / `--check-connection` / `evaluate_live.py` | Yes; configured credentials required | A real provider is called. Connection success does not establish analytic accuracy; full answers still need independent review. |

Semantic/hybrid retrieval additionally calls a configured **embedding API**, even when no answer is generated. Generation and embedding configuration are separate.

Without credentials you cannot evaluate a real LLM answer. Live commands fail with missing variable names and never silently switch to the demo. The demo ignores an arbitrary `--question` and uses a fixed scripted scenario. Its judge scores and Lime decisions are fixtures.

## 1. Run offline engineering checks

The current live answer contract and historical-output audit are documented in
[SOURCE_GROUNDING.md](SOURCE_GROUNDING.md). Focused regression checks use no provider:

```powershell
python -m unittest discover -s tests -p test_grounded_claims.py -v
python audit_grounding.py reports/apinex_prueba_media_actualizada.json --output reports/grounding_review.json
```

The audit packet requires human review of entailment, query meaning and label semantics;
it does not report accuracy from an unannotated sample. Live runs now require a final
`submit_grounded_answer` selection from the source catalog instead of free-form factual prose.

```powershell
python -m unittest discover -s tests -v
python .\run_agent.py original --manager M14 --demo --output .\reports\offline_workflow.json
```

The terminal explicitly reports `OFFLINE SCRIPTED FIXTURE` and zero generation API calls. The JSON labels the mode, holds actual SQL/text evidence and records fixture review/visualization. SVG/CSV files use the real local query rows, but the decision to plot and the written explanation are programmed. Do not report fixture scores as model accuracy.

## 2. Inspect retrieval without generating an answer

```powershell
python .\inspect_rag.py --manager M14 --start 2026-07-01 --end 2026-09-30 --query "recognition contributions acknowledge" --source HR_survey_comments --dimension Recognition --limit 4 --output .\reports\retrieval_only.json
```

Check `retrieval`, `metadata.query`, filters, `corpus_records`, `returned_count`, actual `passages`, dates and `citation_id`. Lexical hits include BM25 scores; lower scores rank first. This command labels `generation_performed=false`. Read the returned passages: matching vocabulary does not guarantee that the passage answers the question.

## 3. Configure and probe a real connection

Start with the **primary GW Azure** connection when the professor provides your group's access. Put only `GW_AZURE_OPENAI_KEY` in the private `.env`. Set the assigned `endpoint`, deployment `model` and `api_version` in the `gw_azure` JSON profile. Use only your group's assigned resource and key; obtain the deployment name from that resource or the professor rather than guessing from the example notebook. API keys stay local and are not committed. JSON contains the non-secret connection settings; unavailable deployment and endpoint values remain empty.

```powershell
python .\run_agent.py --check-connection --profile gw_azure
```

The explicit `--profile gw_azure` uses the same GW deployment for every role, overriding temporary test assignments. No other provider keys are required, and a missing GW setup never falls back to a trial API. If a collaborator already has the API key in their process environment, no `.env` file is needed; non-secret settings still come from JSON.

For NVIDIA/OpenCode, paste only the keys into the private `.env` beside `connections.json`:

```dotenv
NVIDIA_API_KEY=
OPENCODE_API_KEY=
```

The models/endpoints are configured, but live access is not guaranteed. Both NVIDIA profiles use the same `NVIDIA_API_KEY`. On 2026-10-16 OpenCode rejected external free-tier Python requests with HTTP 403 `FreeTierError`, NVIDIA GLM timed out, and NVIDIA Nemotron Ultra returned HTTP 404. Do not present these as working live connections. The OpenCode command below remains an access diagnostic, not a recommendation to use its free tier for Echo. Run the probes separately:

Historical follow-up, 2026-10-16: `nvidia_test` used `nvidia/nemotron-3-super-120b-a12b`, which the user reported answered a plain text request. Both NVIDIA profiles retain 8192 output tokens, with `timeout_seconds=120` and `max_retries=0`. The GLM default retains NVIDIA's documented reasoning settings; a plain diagnostic can omit them in memory. Text completion, tool-call confirmation and full analytic quality are distinct checks. Earlier Echo timeouts occurred with 8192 tokens, so the user's separate 20-token experiments do not establish their cause. `finish_reason=length` now produces an explicit output-token-limit error. Those historical model/endpoint overrides have been removed by the configuration standardization; use the JSON profile instead.

Current configuration, 2026-10-20: `nvidia_test` now selects `nvidia/nemotron-3.5-super-vl-120b-a12b` because NVIDIA deprecated the old Super free endpoint. The new model has a documented free Chat Completions endpoint. The October 16 results below belong to the old model; they are not validation of the new model. Edit the JSON profile to change the model; old `.env` and terminal model overrides are not used.

New-model validation, 2026-10-20: the connection probe passed with `nvidia/nemotron-3.5-super-vl-120b-a12b`, using one real tool call for the shared profile. The ignored local log is `reports/logs/20261020_213401_ec97b74226cb.jsonl`. This establishes connection and minimal tool support; a real manager-question evaluation is still separate. The 19 provider-connection tests also passed.

```powershell
python .\run_agent.py --check-connection --profile nvidia_test
python .\run_agent.py --check-connection --profile nvidia_glm_test
python .\run_agent.py --check-connection --profile opencode_test
```

Follow-up live probes on 2026-10-16 confirmed one real tool call with Nemotron Super, one with GLM-5.3-Flash using a plain request without reasoning options, and one using the configured GLM reasoning options. Both GLM probes took close to two minutes; the configured defaults are retained. Minimal tool access now works for the tested account, but latency and continued availability remain unconfirmed beyond these individual requests. These are minimal API/tool checks, not completed manager analyses. The earlier failures remain historical observations; local logs preserve the follow-up results.

Environment keys take precedence over `.env`. Only live client construction can read that file; inspection and scripted demos do not. New collaborators can copy `.env.example` to a new local `.env` and insert their own keys; `.env` never needs to be shared. If the keys already exist as terminal/system environment variables, no `.env` is required. The shared default is still `gw_azure`, so select a test profile explicitly. These profiles use no paid-model fallback. Check the provider's current free access and limits; the application does not monitor pricing changes.

To test several models in one workflow, assign profiles per role in `connections.json`, as shown in [README.md](README.md#one-connection-layer-selectable-profiles-per-agent). Run `--show-connections` and then `--check-connection` without `--profile` to preserve those mixed assignments. Supplying `--profile` intentionally forces one model profile for all roles. The probe checks each distinct assigned profile once, even if several roles share it.

Inspect assignments first; this does not test the API:

```powershell
python .\run_agent.py --show-connections --profile google_test
```

For Google, set the model and endpoint in the `google_test` JSON profile, then securely enter only the key in the terminal:

```powershell
$env:GOOGLE_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Google API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile google_test
```

For the assigned GW Azure resource, configure `profiles.gw_azure.endpoint` and `model` in JSON first:

```powershell
$env:GW_AZURE_OPENAI_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "GW Azure API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile gw_azure
```

For personal OpenAI, set `profiles.personal_openai.model` and its explicit endpoint in JSON, put `OPENAI_API_KEY` in `.env` or the process environment, and select `--profile personal_openai`. Do not guess deployment availability from the existence of a profile or university account.

The probe makes one actual minimal function call per distinct selected generation profile. A shared profile is tested once and mapped to each role. It supplies no employee data. It does not test embeddings or prove that any analytic answer is correct. No connection was exercised against a real provider during this implementation update.

### APInex SDK trial

The optional `apinex_test` profile uses the existing OpenAI-compatible Chat Completions adapter, base URL `https://api.apinex.bond/v1`, and model ID `free/gpt-6-luna` from the user's APInex setup page. The SDK appends `/chat/completions`; do not add that path to the base URL. APInex's [public API reference](https://apinex.bond/developers) documents this endpoint. This is an Echo Python integration; the site's Codex `/responses` instructions configure a different client.

Put only a fresh key in the ignored local `.env` beside `connections.json`:

```dotenv
APINEX_API_KEY=your_new_key_here
```

Keep the model and endpoint in `connections.json`. Revoke any key exposed in chat before entering its replacement locally. Inspect the profile without API access, then run the tool-call probe after adding the key:

```powershell
python .\run_agent.py --show-connections --profile apinex_test
python .\run_agent.py --check-connection --profile apinex_test
```

The setup page supplied on 2026-10-20 states 5 requests/minute for free access and 30 with a subscription. The user selected one model, Luna, for all five roles and a conservative target of 3 requests/minute. `apinex_test` sets `request_interval_seconds=20` and `rate_limit_retries=2`. One process-wide pacer is shared by roles and registries using the same endpoint and credential, including HTTP 429 retries. It spaces actual request starts, honors a valid `Retry-After` (seconds or HTTP date) when longer than its fallback, and otherwise backs off 20 then 40 seconds before its two retries. Exhaustion still reports the existing safe HTTP error; the cooldown remains shared. SDK `max_retries=0` prevents hidden retries from bypassing pacing. Execution API-call counters include these actual retry attempts. Wait/retry events record timing only, without keys or response payloads. Separate terminal processes or other applications using the key are not coordinated by this in-process pacer.

The existing workflow defaults remain 32 model turns, 48 local tool calls and 300 seconds elapsed time; specialist loops also have their own turn bounds. These prevent runaway loops and are distinct from requests/minute. HTTP retries count in execution API-call totals, not as new logical workflow turns. Deliberate pacing waits consume elapsed time. For a longer Original/Vanilla run, explicitly add `--run-seconds 900` (15 minutes); this does not increase the model-turn limit. Time limits are checked at budget checkpoints, not by forcibly cancelling an in-flight request or wait.

The minimal probe checks one real tool call, not analytical quality or sustained throughput. On 2026-10-20, the local connection probe confirmed one real Luna tool call. The first medium analytic run (`reports/apinex_prueba_media.json`) completed 17 API calls but failed because no valid structured verifier review was obtained; Vanilla also failed quote validation. The shared default remains `gw_azure`; `--profile apinex_test` selects Luna for every role in that run. Its output allowance is now 6000 tokens per request for all roles, raised from 3500 to allow more space for classifications and structured reviews. This is a maximum, not a requested response size; support and analytical quality after the corrections require a separate live test.

The 2026-10-20 workflow corrections support multiple planned metrics, retain Cherry's query tools, expose numeric task coverage, allow literal sentiment excerpts up to 400 characters, repair only invalid records within a classification batch, and identify structured review errors by field/code. Run the focused regression checks without a model or API:

```powershell
python -m unittest discover -s tests -p test_workflow_repairs.py -v
```

Then run the full suite. Prescribed model responses test software contracts, not model reasoning. For a real follow-up, repeat the same original medium question/scope with `--profile apinex_test --run-seconds 1000` and a new output filename, preserving the earlier failed artifact. Run only one terminal process per key because pacing is shared within a process.

## 4. Run a live answer with lexical RAG

```powershell
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --question "Review recognition using quarterly survey metrics and supportive and critical anonymous comments. Include an indicator chart if supported." --output .\reports\live_review.json
```

Omit `--demo`: this is essential. All five model roles use the selected profile. The workflow runs Lime for each candidate and ZeroSugar reviews the answer/chart plan before local export. `execution.successful_generation_api_calls` counts successful adapter requests; `profiles_used` records the actual model/deployment names. The offline value is always zero.

## 5. Test semantic/hybrid RAG aligned with the classroom notebook

Configure `profiles.google_embeddings.model` in `connections.json` with an embedding model actually available to the same Google account:

```powershell
python .\inspect_rag.py --manager M14 --query "recognition of work contributed to another team" --retrieval semantic --embedding-profile google_embeddings --limit 4 --output .\reports\semantic_retrieval.json
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --retrieval hybrid --embedding-profile google_embeddings --question "What recognition metrics and anonymous comments support a manager follow-up?" --output .\reports\hybrid_review.json
```

Azure uses the `gw_embeddings` JSON profile; personal OpenAI uses `openai_embeddings`. Set the corresponding `model` and `endpoint` in JSON. Start with one quarter: initial document embedding can make many requests and sends scoped passage text to the selected provider. Local caches reuse document vectors but query embeddings still require the provider. There is no automatic semantic-to-lexical fallback.

## How to demonstrate RAG rather than just claim it

The actual path is `ScopedData.text_documents` -> `TextSearch` or `SemanticTextSearch` -> `search_text` result -> tool-result context in the next `model.respond` -> cited Vanilla answer -> ZeroSugar source checks. This is the classroom retrieval/context/generation pattern implemented with function tools.

Inspect a saved Original artifact:

1. Find the Vanilla entry in `delegations` and its `tool_trace` search calls. Confirm queries, filters, retrieval method, passage text and citation IDs.
2. Check `rag.specialist_runs`: `context_supplied_to_generator`, returned IDs, `cited_ids` and `generation_mode`. Direct Vanilla runs store the same information directly in `rag`.
3. In semantic/hybrid results, inspect embedding identity, cosine scores and ranking method. Scores are retrieval ordering, not confidence or prevalence.
4. Match answer claims to the passages themselves and independently check relevance/entailment. Citation existence alone is insufficient.
5. Confirm live mode and successful generation API calls. An offline fixture can demonstrate that context reaches a simulated call, but is not proof of live grounded reasoning.

RAG is not necessarily used on every Original run: a purely numerical question can use Cherry alone. An empty search is recorded with no returned IDs and `context_supplied_to_generator=false`; do not describe that as a grounded textual answer. SQL evidence is structured grounding, distinct from Vanilla's textual RAG. Systematic sentiment classification enumerates the full eligible population rather than ranking passages; it is recorded separately in `sentiment`, not misrepresented as ranked textual RAG.

## Sentiment implementation versus model quality

The `survey_sentiment` live case asks Original for Recognition sentiment percentages in one quarter. Confirm that Vanilla actually calls `analyze_survey_sentiment`, covers all eligible IDs, preserves per-comment labels/excerpts/source hashes, includes mixed/indeterminate in the denominator and discloses `human_validated=false`. ZeroSugar must recompute the summary and reject altered counts or source provenance. Source lookup and aggregation validation cannot establish the semantic accuracy of every model label.

Offline sentiment tests use prescribed labels solely to check those contracts, batch completeness, failures, privacy fields and arithmetic. They do not classify the actual survey corpus or evaluate intelligence. Human quality evaluation must use independently annotated held-out comments across categories/dimensions, per-category precision/recall, a confusion matrix and inspection of ambiguous/mixed cases. No measured quality result is available while the API remains unconfigured.

## Fixed live evaluation cases

```powershell
python .\evaluate_live.py --list
python .\evaluate_live.py --case recognition_counts --profile google_test
python .\evaluate_live.py --case textual_views --profile google_test --retrieval hybrid --embedding-profile google_embeddings
python .\evaluate_live.py --case recognition_chart --profile google_test
```

This runner has no demo option. It sends only the case question/scope, never its expected criteria. It records duration, execution status, answer artifact and a separate human-review record. Missing configuration is recorded as `execution_failed`, not a successful simulated benchmark. Exit 0 means execution completed, not that an independent reviewer found the answer correct; exit 2 requires revision.

Review SQL against independent source calculations, passage relevance, units, denominators, privacy and chart-question correspondence. Record unsupported/incorrect/refused cases as well. Compare the same cases and scopes across profiles; do not treat a small synthetic evaluation as production performance.

## Chart inspection

Accepted exports contain SVG graphics, exact selected CSV columns and JSON with source SQL/scope. Lime chooses the specification; the renderer never uses model-generated numbers. Check the visible title/axes, missing values, series and source/date footer against the CSV. SVG is a local artifact, not a frontend. ZeroSugar checks structured specifications; it does not see pixels. A general report/dashboard system is not implemented; `recognition_report.py` remains a separate fixed-report utility.

The classroom references and implementation mapping are in [REFERENCE_VALIDATION.md](REFERENCE_VALIDATION.md); role-specific examples are in [AGENT_ROLES.md](AGENT_ROLES.md).
