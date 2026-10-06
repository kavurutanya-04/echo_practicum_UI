# Validation against classroom references

Updated on 2026-10-06 after re-reading the classroom Text-to-SQL, RAG, benchmark and judge notebooks and the shared agent transcripts. This is a source-code and offline integration review, not a claim of successful access to GW, Google or OpenAI.

## Findings and resulting implementation

| Reference inspected | What the example demonstrates | Echo comparison and resulting behavior |
| --- | --- | --- |
| `References/GWU_LLM_examples/basic_config_connect.ipynb`, code cells 4, 6, 8 | Assigned Azure endpoint, `GW_AZURE_OPENAI_KEY`, separate Chat/Responses calls and embedding deployment | `gw_azure` preserves the professor's AzureOpenAI/Responses pattern and preview API version. The resource and deployment come from environment variables. Azure v1 is an optional profile setting. No hardcoded `gw-sb-01` or interactive key prompt is used by agent code. |
| `text2sql_example/text_to_sql.ipynb`, code cells 2, 4, 6 | In-memory SQLite, question-to-SQL, few-shot examples and a single-SELECT string check | Cherry obtains a scoped schema and chooses SQL through function calls. The executor adds physical data isolation, SQLite authorization, query-only mode and execution/result limits. CTEs are supported; a string prefix alone is not treated as the security boundary. Source count reconciliation and prohibited-query tests pass. |
| `embedding_example/get_embeddings.ipynb`, code cells 2 and 3 | Batch embeddings, persistent vectors and stable record IDs | Optional semantic/hybrid retrieval now creates scoped, reusable local vector caches. Text-generation and embedding profiles are separate. Document hashes deduplicate embedding requests; provider/model/endpoint/scope changes produce separate caches. Completed batches persist if a later request fails. |
| `rag_example/rag_query.ipynb`, code cells 2, 4, 6 | Query embedding, cosine similarity, retrieved context and cited generation | Original Vanilla was lexical-only. It now supports lexical, semantic and hybrid retrieval. The semantic path uses normalized vectors/cosine similarity, source/date metadata and scope filters before ranking. Its math/cache behavior is tested with deterministic vectors; real provider embedding quality remains untested. |
| `llm_as_judge_example/llm_as_judge.ipynb` | Seven independently scored 1-3 rubric dimensions, rationale and uncertainty in structured output | ZeroSugar applies the same dimension names, with an evidence-aware verification contract. It combines a model review with citation/scope checks, SQL replay and text/source comparison. Code can force revision even if the model says accept. Judge results are fallible and require human review. |
| `benchmark_example/mini_benchmark.ipynb` | Fixed cases and expected outcomes kept separate from generation | Offline tests have independent scoped-source checks and negative cases. `tests/evaluation_cases.json` supplies representative live cases and review criteria; it is not indexed or supplied as an answer source. Live answer accuracy and provider comparisons have not been measured. |
| `Resources/AI agents explained_ Build your first agent in 8 minutes.txt`, approximately 03:25-07:07 | Agents with separate roles, shared output state, agents exposed as tools, validation and bounded retries | Original exposes Cherry/Vanilla as tools and collects their results. ZeroSugar reviews each candidate. One revision is permitted; a twice-rejected answer is withheld. Structured verdict validation replaces an ambiguous free-text `ok`/`retry` contract. |
| `Resources/preagent1.PNG`, `agent0.PNG`, `agent6.PNG`, `agent8.PNG`, `agent11.PNG`, `agent13.PNG` | Behavior patterns, ADK role definitions, output keys, checker instructions and root/specialist topology | The same separation of responsibilities is implemented with a small provider-independent Python runtime. Google ADK is not a dependency; selecting Gemini does not require replacing the runtime or tools. Screenshots were inspected as educational illustrations, not as executable package documentation. |
| `Resources/Local AI Agents In 26 Minutes.txt`, approximately 02:27-09:59 and 11:47-15:41 | Local execution, configurable models, tools, multi-agent roles, isolation and traces | Echo's code/tools run locally while inference can use a configured cloud provider. Model profiles are independent of agent roles. Tools have restricted capabilities and artifacts retain delegations, evidence and verification history. Persistent personal memory, desktop/email access and scheduling are outside this prototype's current scope. |

## Connection architecture

`connections.json` is a catalog of connection profiles, not a secrets file. Each role selects a profile. Roles using the same profile share one stateless API client/adapter; each run maintains its own instructions and conversation history. Separate profile selections permit different providers or deployments by role.

Google uses its documented OpenAI-compatible Chat Completions and embeddings endpoints. The adapter preserves tool-call metadata, including thought signatures, rather than stripping it from follow-up calls. GW Azure uses the classroom Responses configuration by default. Endpoint/deployment compatibility cannot be inferred from successful mocks.

Selection precedence is: CLI `--profile` for all roles in that run; then role-specific environment override; then role-specific JSON setting; then `ECHO_DEFAULT_PROFILE`; then the JSON default. Embedding profile selection is explicit and separate from generation. No automatic fallback sends data to another provider.

## Evidence from local tests

The 61 offline tests pass. They cover source reconciliation, read-only SQL controls, manager/date isolation, anonymous provenance, retrieval filters/deduplication, provider configuration and tool-message contracts, embedding/cache math, altered evidence, review schema validation, compulsory verification, revision/withholding, shared budgets, missing live configuration, evidence-bound chart export, retrieval context supplied to subsequent generation, and full-population sentiment classification contracts. Sentiment tests use prescribed labels to verify complete batch coverage, exact excerpts, source hashes, denominator arithmetic, suppression, failure withholding and independent artifact review; they do not establish model classification quality. The source database hash is unchanged after the workflow checks.

The five-role offline demonstration produces a JSON artifact, local SVG/CSV chart exports, child results, source evidence, RAG traces and verification records. Every offline answer, chart-selection decision and rubric score is explicitly marked as scripted. Such scores are fixtures, not model performance measurements. The 2026-10-06 check is under ignored `reports/review_20261006`.

## Resulting changes from the 2026-10-06 review

Lime is the canonical name of the fifth agent (formerly Visualizer). Data passed to it is limited to SQL evidence labeled as produced by Cherry. The code, role profiles, examples and diagram use Lime consistently. Vanilla now has an executable systematic survey sentiment tool, a defined five-label rubric and code-computed scoped percentages, with full source-linked labels in the output artifact. Live reasoning and sentiment-quality evaluation remain pending: API configuration is deferred, and no human-validated classifier accuracy or real sentiment result is claimed. Lime does not consume Vanilla's sentiment summaries directly.

- Executable instructions now include role-specific worked examples, input/output expectations and prohibited behaviors. [AGENT_ROLES.md](AGENT_ROLES.md) provides the complete role contracts.
- The shared 8-minute agent example explicitly separates specialists and validators with concrete outputs. Echo adds Lime as a fifth model role, invoked automatically after each candidate. It chooses relevant indicators/type/axes/units from existing SQL rows; it does not run unrestricted generated code.
- Concrete rendering is `LimeAgent.export` using `chart_export.py`, producing SVG, CSV and source metadata after ZeroSugar accepts. ZeroSugar reviews numeric references and chart semantics, while visual layout inspection remains separate. No frontend/dashboard was built.
- The classroom benchmark actually calls a provider. Accordingly, `evaluate_live.py` has no demo mode and keeps expected criteria outside agent input; missing credentials produce a failed evaluation record. `--check-connection` is an actual minimal function-call probe, not just a configuration printout.
- The classroom RAG notebook performs retrieval -> source context -> cited generation. `inspect_rag.py` makes the retrieval step inspectable; saved runs expose queries/filters, method, scores, source IDs, context delivery and citations. A test inspects the next generation-call history to confirm that retrieved text reached it. Semantic embedding/relevance quality is still untested against a real provider.
- [TESTING_AND_RAG.md](TESTING_AND_RAG.md) distinguishes offline checks, retrieval-only diagnostics and real API-backed evaluation. Profile/model request counts are recorded without credentials.

## Remaining live validation

1. Select a configured model profile with access to tools. Use Google for initial tests if desired; use the university's assigned resource/deployment for GW tests when credentials are available.
2. Run the fixed cases in `tests/evaluation_cases.json` against identical manager/date scopes. Inspect generated SQL and compare numeric results with independent source queries. Record failed/refused cases too.
3. Test semantic/hybrid retrieval with a separately configured embedding profile. Check whether retrieved passages actually address each question and preserve source IDs; compare against lexical retrieval on the same cases.
4. Review ZeroSugar's claim judgments manually, including intentional wrong numbers, incorrect citations, prompt injection in source text and anonymous identification attempts. A model's acceptance alone is not a correctness guarantee.
5. Record provider/model/deployment, latency, tool calls, evidence correctness and final answer quality. Do not describe a small classroom evaluation as production performance.

Authentication and production deployment remain separate work. CLI manager selection is a demonstration scope; a real interface must derive it from authenticated permissions. All project data is synthetic, and findings support human review.

## Primary documentation checked

- [OpenAI: coordinator with agents as tools](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [Microsoft: Azure OpenAI Responses API](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses)
- [Google: OpenAI-compatible API, function calling and embeddings](https://ai.google.dev/gemini-api/docs/openai)
- [OpenAI: function calling, schemas and tool-result context](https://developers.openai.com/api/docs/guides/function-calling), checked 2026-10-06
- [Anthropic: building effective agents](https://www.anthropic.com/engineering/building-effective-agents), reviewed in the architecture discussion; specialist boundaries and verification complement the classroom examples.

Classroom source files remain unchanged. License attribution for educational adaptations is in `THIRD_PARTY_NOTICES.md`.
