# Validation against classroom references

Classroom-source inspection: 2026-10-06. Current implementation comparison reviewed:
2026-10-21, against local code/configuration and the documented runs. This refresh does
not claim that classroom notebooks, external documentation or provider access were newly
tested. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) records observed live outcomes;
[DOCUMENTATION_MAP.md](DOCUMENTATION_MAP.md) routes current and historical references.

Current v3 addendum, 2026-10-21: narrative digits/quantifiers now flag semantic review
instead of causing automatic rejection. Text or row interpretations may use quote=null
with one or several sources; exact example quotes, scope, coverage and controlled
arithmetic remain checked. Earlier test/pass descriptions below are historical and do
not validate v3. No tests, classroom reinspection or API calls were run for this change.
See [SOURCE_GROUNDING.md](SOURCE_GROUNDING.md) for the current executable contract.

## Findings and resulting implementation

| Reference inspected | What the example demonstrates | Echo comparison and resulting behavior |
| --- | --- | --- |
| `References/GWU_LLM_examples/basic_config_connect.ipynb`, code cells 4, 6, 8 | Assigned Azure endpoint, `GW_AZURE_OPENAI_KEY`, separate Chat/Responses calls and embedding deployment | `gw_azure` preserves the professor's AzureOpenAI/Responses pattern and preview API version. Resource, deployment and API version now come from `connections.json`; only credentials use environment/private `.env`. Azure v1 is optional. No hardcoded classroom resource or interactive key prompt is used by agent code. |
| `text2sql_example/text_to_sql.ipynb`, code cells 2, 4, 6 | In-memory SQLite, question-to-SQL, few-shot examples and a single-SELECT string check | Cherry obtains a scoped schema and chooses SQL through function calls. The executor adds physical data isolation, SQLite authorization, query-only mode and execution/result limits. CTEs are supported; a string prefix alone is not treated as the security boundary. Source count reconciliation and prohibited-query tests pass. |
| `embedding_example/get_embeddings.ipynb`, code cells 2 and 3 | Batch embeddings, persistent vectors and stable record IDs | Optional semantic/hybrid retrieval now creates scoped, reusable local vector caches. Text-generation and embedding profiles are separate. Document hashes deduplicate embedding requests; provider/model/endpoint/scope changes produce separate caches. Completed batches persist if a later request fails. |
| `rag_example/rag_query.ipynb`, code cells 2, 4, 6 | Query embedding, cosine similarity, retrieved context and cited generation | Original Vanilla was lexical-only. It now supports lexical, semantic and hybrid retrieval. The semantic path uses normalized vectors/cosine similarity, source/date metadata and scope filters before ranking. Its math/cache behavior is tested with deterministic vectors; real provider embedding quality remains untested. |
| `llm_as_judge_example/llm_as_judge.ipynb` | Seven independently scored 1-3 rubric dimensions, rationale and uncertainty in structured output | ZeroSugar applies the same dimension names, with an evidence-aware verification contract. It combines a model review with citation/scope checks, SQL replay and text/source comparison. Code can force revision even if the model says accept. Judge results are fallible and require human review. |
| `benchmark_example/mini_benchmark.ipynb` | Fixed cases and expected outcomes kept separate from generation | Offline tests have independent scoped-source checks and negative cases. `tests/evaluation_cases.json` supplies representative live cases and review criteria; it is not indexed or supplied as an answer source. Live answer accuracy and provider comparisons have not been measured. |
| `Resources/AI agents explained_ Build your first agent in 8 minutes.txt`, approximately 03:25-07:07 | Agents with separate roles, shared output state, agents exposed as tools, validation and bounded retries | Original exposes Cherry/Vanilla as tools; ZeroSugar reviews candidate claims. One repair round is permitted. Unresolved output can release only independently supported eligible claims, with charts withheld; integrity/safety failures block release. Structured verdicts replace an ambiguous free-text `ok`/`retry` contract. |
| `Resources/preagent1.PNG`, `agent0.PNG`, `agent6.PNG`, `agent8.PNG`, `agent11.PNG`, `agent13.PNG` | Behavior patterns, ADK role definitions, output keys, checker instructions and root/specialist topology | The same separation of responsibilities is implemented with a small provider-independent Python runtime. Google ADK is not a dependency; selecting Gemini does not require replacing the runtime or tools. Screenshots were inspected as educational illustrations, not as executable package documentation. |
| `Resources/Local AI Agents In 26 Minutes.txt`, approximately 02:27-09:59 and 11:47-15:41 | Local execution, configurable models, tools, multi-agent roles, isolation and traces | Echo's code/tools run locally while inference can use a configured cloud provider. Model profiles are independent of agent roles. Tools have restricted capabilities and artifacts retain delegations, evidence and verification history. Persistent personal memory, desktop/email access and scheduling are outside this prototype's current scope. |

## Connection architecture

`connections.json` is a catalog of connection profiles, not a secrets file. Each role selects a profile. Roles using the same profile share one stateless API client/adapter; each run maintains its own instructions and conversation history. Separate profile selections permit different providers or deployments by role.

Google uses its documented OpenAI-compatible Chat Completions and embeddings endpoints. The adapter preserves tool-call metadata, including thought signatures, rather than stripping it from follow-up calls. GW Azure uses the classroom Responses configuration by default. Endpoint/deployment compatibility cannot be inferred from successful mocks.

Selection precedence is CLI `--profile` for all roles in that run, then role-specific
JSON assignment, then JSON `default_profile`. Old model/endpoint/role environment overrides
are not used. Only API keys use process-environment precedence over the ignored `.env`.
Embedding profile selection is separate from generation. No automatic fallback sends data
to another provider. The user currently selects optional `apinex_test`/Luna for every role;
the shared JSON default remains `gw_azure`.

## Evidence from local tests

The initial 2026-10-06 review passed 61 offline tests. The latest implementation check
on 2026-10-21 passed 207, including source-bound claims, shared policies/clarification,
request pacing, minimized rejection diagnostics and 22 sentiment-workflow regressions.
The new checks exercise three-attempt repair with retained valid records/counters,
incompatible-task declines, canonical comment sources, incomplete coverage and independent
artifact review. Prescribed labels establish software behavior, not classification quality.
The original database-integrity result belongs to that historical test run; this
documentation refresh did not rerun tests or compute a new database hash.

The five-role offline demonstration produces a JSON artifact, local SVG/CSV chart exports, child results, source evidence, RAG traces and verification records. Every offline answer, chart-selection decision and rubric score is explicitly marked as scripted. Such scores are fixtures, not model performance measurements. The 2026-10-06 check is under ignored `reports/review_20261006`.

## Resulting changes from the 2026-10-06 review

At that review, Lime became the canonical fifth role (formerly Visualizer), using only
Cherry-produced SQL evidence. Vanilla gained full-population sentiment classification
and code-computed summaries. Later live evaluation began: Luna's fourth run completed a
numeric comparison, while the fifth retained a complete child classification but failed
before independent review or release. Its routing/retry/source repairs now await a sixth
live run. No independently measured classifier accuracy is available. Lime still does
not consume Vanilla's sentiment summaries directly.

- Executable instructions now include role-specific worked examples, input/output expectations and prohibited behaviors. [AGENT_ROLES.md](AGENT_ROLES.md) provides the complete role contracts.
- The shared 8-minute agent example separates specialists and validators with concrete outputs. Echo's fifth role, Lime, runs only when a chart is planned. It chooses indicators/type/axes/units from existing SQL rows; it does not execute generated code.
- Concrete rendering is `LimeAgent.export` using `chart_export.py`, producing SVG, CSV and source metadata after ZeroSugar accepts. ZeroSugar reviews numeric references and chart semantics, while visual layout inspection remains separate. No frontend/dashboard was built.
- The classroom benchmark actually calls a provider. Accordingly, `evaluate_live.py` has no demo mode and keeps expected criteria outside agent input; missing credentials produce a failed evaluation record. `--check-connection` is an actual minimal function-call probe, not just a configuration printout.
- The classroom RAG notebook performs retrieval -> source context -> cited generation. `inspect_rag.py` makes the retrieval step inspectable; saved runs expose queries/filters, method, scores, source IDs, context delivery and citations. A test inspects the next generation-call history to confirm that retrieved text reached it. Semantic embedding/relevance quality is still untested against a real provider.
- [TESTING_AND_RAG.md](TESTING_AND_RAG.md) distinguishes offline checks, retrieval-only diagnostics and real API-backed evaluation. Profile/model request counts are recorded without credentials.

## Remaining live validation

1. Repeat the fifth Recognition-comments question with `apinex_test`, the same M14/Q3 2026 scope and a new sixth-run output filename. Inspect actual Vanilla coverage, individual citations, ZeroSugar review, rejection diagnostics and calls/tokens. Use only one process per key for shared pacing. See the exact command in [TESTING_AND_RAG.md](TESTING_AND_RAG.md#next-live-test-sixth-luna-run).
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
