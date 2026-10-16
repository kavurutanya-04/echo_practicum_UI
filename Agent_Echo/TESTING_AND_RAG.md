# What can be tested without an API, and how to verify RAG

Updated 2026-10-16. Run commands inside `Final_Project/Agent_Echo` with the project's Python environment. `.env.example` is a reference; live clients can load keys, endpoints, deployment/model names and API versions from the private, Git-ignored `.env`. Profile selection stays in `connections.json` or terminal variables. Never put real keys in files committed to Git. GW Azure is the primary/final provider; all other profiles are optional tests.

## Three different activities

For evaluating intelligence, use the live evaluation cases after configuring a provider. Running Python locally can still call a cloud LLM; the decisive distinction is live API responses versus programmed fixtures. The demo is an optional engineering diagnostic, not a reasoning benchmark. NVIDIA/OpenCode profiles are prepared; live connection and quality checks are pending private keys.

| Activity | Calls an API? | What the result establishes |
| --- | --- | --- |
| Unit/integration tests and `--demo` | No; scripted/mocked responses | Queries, restrictions, retrieval plumbing, rendering, review gates and error handling work on those cases. It does not evaluate LLM reasoning, chart selection or answer quality. |
| `inspect_rag.py --retrieval lexical` | No | Real local passages can be retrieved with source IDs and scope. No generated answer is produced. |
| Live agents / `--check-connection` / `evaluate_live.py` | Yes; configured credentials required | A real provider is called. Connection success does not establish analytic accuracy; full answers still need independent review. |

Semantic/hybrid retrieval additionally calls a configured **embedding API**, even when no answer is generated. Generation and embedding configuration are separate.

Without credentials you cannot evaluate a real LLM answer. Live commands fail with missing variable names and never silently switch to the demo. The demo ignores an arbitrary `--question` and uses a fixed scripted scenario. Its judge scores and Lime decisions are fixtures.

## 1. Run offline engineering checks

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

Start with the **primary GW Azure** connection when the professor provides your group's access. Fill in the private `.env` with `GW_AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` and `AZURE_OPENAI_API_VERSION=2025-03-01-preview`. Use only your group's assigned resource and key; obtain the deployment name from that resource or the professor rather than guessing from the example notebook. These values are read locally and are not committed to GitHub.

```powershell
python .\run_agent.py --check-connection --profile gw_azure
```

The explicit `--profile gw_azure` uses the same GW deployment for every role, overriding temporary test assignments. No other provider keys are required, and a missing GW setup never falls back to a trial API. If a collaborator already has the named variables in their terminal/system environment, no `.env` file is needed.

For NVIDIA/OpenCode, paste only the keys into the private `.env` beside `connections.json`:

```dotenv
NVIDIA_API_KEY=
OPENCODE_API_KEY=
```

The models/endpoints are configured, but live access is not guaranteed. Both NVIDIA profiles use the same `NVIDIA_API_KEY`. On 2026-10-16 OpenCode rejected external free-tier Python requests with HTTP 403 `FreeTierError`, NVIDIA GLM timed out, and NVIDIA Nemotron Ultra returned HTTP 404. Do not present these as working live connections. The OpenCode command below remains an access diagnostic, not a recommendation to use its free tier for Echo. Run the probes separately:

```powershell
python .\run_agent.py --check-connection --profile nvidia_test
python .\run_agent.py --check-connection --profile nvidia_glm_test
python .\run_agent.py --check-connection --profile opencode_test
```

Environment keys take precedence over `.env`. Only live client construction can read that file; inspection and scripted demos do not. New collaborators can copy `.env.example` to a new local `.env` and insert their own keys; `.env` never needs to be shared. If the keys already exist as terminal/system environment variables, no `.env` is required. The shared default is still `gw_azure`, so select a test profile explicitly. These profiles use no paid-model fallback. Check the provider's current free access and limits; the application does not monitor pricing changes.

To test several models in one workflow, assign profiles per role in `connections.json` or use the terminal overrides shown in [README.md](README.md#one-connection-layer-selectable-profiles-per-agent). Run `--show-connections` and then `--check-connection` without `--profile` to preserve those mixed assignments. Supplying `--profile` intentionally forces one model profile for all roles. The probe checks each distinct assigned profile once, even if several roles share it.

Inspect assignments first; this does not test the API:

```powershell
python .\run_agent.py --show-connections --profile google_test
```

For Google, set the model name available to your account and securely enter the key in the same terminal:

```powershell
$env:GOOGLE_MODEL = "YOUR-TOOL-CAPABLE-MODEL"
$env:GOOGLE_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Google API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile google_test
```

For the assigned GW Azure resource:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-ASSIGNED-RESOURCE.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "YOUR-RESPONSES-CAPABLE-DEPLOYMENT"
$env:GW_AZURE_OPENAI_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "GW Azure API key" -AsSecureString)).Password
python .\run_agent.py --check-connection --profile gw_azure
```

For personal OpenAI, set `OPENAI_MODEL` and `OPENAI_API_KEY`, and select `--profile personal_openai`. Do not guess deployment availability from the existence of a profile or university account.

The probe makes one actual minimal function call per distinct selected generation profile. A shared profile is tested once and mapped to each role. It supplies no employee data. It does not test embeddings or prove that any analytic answer is correct. No connection was exercised against a real provider during this implementation update.

## 4. Run a live answer with lexical RAG

```powershell
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --question "Review recognition using quarterly survey metrics and supportive and critical anonymous comments. Include an indicator chart if supported." --output .\reports\live_review.json
```

Omit `--demo`: this is essential. All five model roles use the selected profile. The workflow runs Lime for each candidate and ZeroSugar reviews the answer/chart plan before local export. `execution.successful_generation_api_calls` counts successful adapter requests; `profiles_used` records the actual model/deployment names. The offline value is always zero.

## 5. Test semantic/hybrid RAG aligned with the classroom notebook

Configure an embedding model actually available to the same Google account:

```powershell
$env:GOOGLE_EMBEDDING_MODEL = "YOUR-AVAILABLE-TEXT-EMBEDDING-MODEL"
python .\inspect_rag.py --manager M14 --query "recognition of work contributed to another team" --retrieval semantic --embedding-profile google_embeddings --limit 4 --output .\reports\semantic_retrieval.json
python .\run_agent.py original --manager M14 --start 2026-07-01 --end 2026-09-30 --profile google_test --retrieval hybrid --embedding-profile google_embeddings --question "What recognition metrics and anonymous comments support a manager follow-up?" --output .\reports\hybrid_review.json
```

Azure uses `gw_embeddings` plus `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`; personal OpenAI uses `openai_embeddings` plus `OPENAI_EMBEDDING_MODEL`. Start with one quarter: initial document embedding can make many requests and sends scoped passage text to the selected provider. Local caches reuse document vectors but query embeddings still require the provider. There is no automatic semantic-to-lexical fallback.

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
