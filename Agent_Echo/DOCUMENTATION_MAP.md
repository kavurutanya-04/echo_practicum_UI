# Echo documentation map

Current update, 2026-10-27: [RESUME_AND_CAPTURE.md](RESUME_AND_CAPTURE.md) supersedes v4's
literal reconstruction with review-v5, documents full private exchanges/checkpoints,
credential omission and phase-only `--resume`. Runtime sources include agents/capture.py,
agents/resume.py, model/execution logging, role entry points and run_agent.py. Readmes,
roles, source grounding, context, project guidance, UI types and the testing guide are
aligned. [Runs 30-32 and retry commands](TESTING_AND_RAG.md#next-three-model-runs-30-32-2026-10-27)
are pending user execution. No local tests, build, API call or publication; prior test
totals do not validate this update. [History](LIVE_TEST_HISTORY.md) includes runs 27-29.

Current update, 2026-10-27: [review-v4](WORKFLOW_RELIABILITY.md#assertion-level-support-review-review-v4-2026-10-27)
adds explicit per-assertion evidence assessments, coverage/reference validation and
whole-finding withholding on a failed assertion. Roles, source grounding, README, context,
project guidance and UI types/details are aligned. [322 offline checks and the frontend
build](TESTING_AND_RAG.md#assertion-level-support-review-2026-10-27) passed; live semantic
quality and expanded-provider-schema compatibility remain unverified. The new
[LIVE_TEST_HISTORY.md](LIVE_TEST_HISTORY.md) compares runs 15-26 and distinguishes changes
applied after each run from that run's results. Older dated entries remain history.

Reviewed: 2026-10-26 (America/New_York), against the current local implementation
and the saved live artifacts through run eighteen. Current answers use source-facts-v4;
historical test/replay counts below predate it. This is an index and maintenance guide, not an
additional runtime policy or a benchmark. No new provider request was made for this review.

## Current entry points and responsibilities

| Reference | Purpose and authority |
| --- | --- |
| [Workspace guidance](../../AGENTS.md) | Routes Practicum work to the Echo project; also covers unrelated coursework. Local parent file, outside the Echo Git repository. |
| [Project guidance](../AGENTS.md) | Instructions for the coding assistant maintaining Echo; read with the context file once per chat. Echo does not load this file as an agent prompt. |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Compact current state, observed runs, approved decisions and next test. |
| [Repository README](../README.md) | Clone/setup, repository contents and collaboration. |
| [Application README](README.md) | Running Echo, configuration, artifacts, statuses and data access. |
| [UI README](../Echo_UI/README.md) | Group-built local manager UI and technical console; its startup script targets macOS/Linux. Current Windows startup evidence and command are recorded in PROJECT_CONTEXT.md. |
| [AGENT_ROLES.md](AGENT_ROLES.md) | Responsibilities, tools, inputs/outputs and boundaries of all five roles. |
| [WORKFLOW_RELIABILITY.md](WORKFLOW_RELIABILITY.md) | Planning, bounded retries, declines, retained evidence, structured repair feedback, independent review, release gates and minimized diagnostics. |
| [SOURCE_GROUNDING.md](SOURCE_GROUNDING.md) | Source-bound numeric facts, cited synthesis, literal examples, v2 presentation and v1 replay compatibility. |
| [TESTING_AND_RAG.md](TESTING_AND_RAG.md) | Offline checks, provider probes, live evaluation, pacing and retrieval inspection. Latest suite result is dated there; a test count is not classifier accuracy. |
| [REFERENCE_VALIDATION.md](REFERENCE_VALIDATION.md) | Historical classroom comparison with current implementation corrections. Historical source-review dates are distinct from the current documentation review. |
| [Dataset README](../files_update/README.md) | Synthetic source definitions, periods, denominators and privacy assumptions; runtime behavior belongs to the code and application guides. |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | Attribution and reproduced license text. Preserve notices; do not rewrite them as project status. Reviewed without changing the license. |

## Executable configuration and instructions

| Source | Controls |
| --- | --- |
| [connections.json](connections.json) and [connections.py](agents/connections.py) | Non-secret model/endpoint/API settings, limits, role selection and key loading. Only key values come from process variables or ignored `.env`. |
| [.env.example](.env.example) | Empty key-name template; never actual credentials. |
| [policies.py](agents/policies.py) | Six common rules composed into analysis/model calls. This is the executable policy source, separate from coding-assistant guidance. |
| [Original](agents/original.py), [Cherry](agents/cherry.py), [Vanilla](agents/vanilla.py), [Lime](agents/lime.py), [ZeroSugar](agents/zero_sugar.py) | Role-specific prompts, tools and call paths. Shared rules do not transfer SQL, classification or verification ownership. |
| [run_agent.py](run_agent.py), [runtime.py](agents/runtime.py), [data_access.py](agents/data_access.py), [grounding.py](agents/grounding.py) | CLI scope/options, execution, source restrictions and deterministic checks. Code is authoritative when prose disagrees. |

## Local background and historical drafts

These four files are intentionally ignored by the repository and may be absent from a
clone. Their current-status notes were reviewed locally; inclusion here does not publish
them or approve their proposals.

| Local reference | How to use it |
| --- | --- |
| [technical_setup_agents.md](../technical_setup_agents.md) | Current local setup directions plus the distinction between installed SDKs and implemented adapters. |
| [echo_brainstorm_resumen_y_decisiones.md](../echo_brainstorm_resumen_y_decisiones.md) | Product/architecture proposals and unresolved decisions. Current reliability repairs preserve the five roles; proposed business execution is not implemented. |
| [brainstorm_employee_engagement.md](../brainstorm_employee_engagement.md) | September problem exploration, retained as history rather than current runtime specifications. |
| [alternativas_employee_engagement.md](../alternativas_employee_engagement.md) | September project/market comparison, not a refreshed market assessment or final selection. |

## Reasoned actions and review simplification after run twenty-three (2026-10-27)

The [current workflow](WORKFLOW_RELIABILITY.md#reasoned-actions-and-review-simplification-after-run-twenty-three-2026-10-27)
records the mandatory reasoned action for Original and a support-only contextual policy
correction, separate from user-requested completeness. Context, roles, source grounding,
README and testing guide are aligned. Novel action ideas remain proposals; objective
gates and prior artifacts remain. The [88 focused checks](TESTING_AND_RAG.md#reasoned-actions-and-review-simplification-after-run-twenty-three-2026-10-27)
do not establish improved live model judgment. No API call or publication.

## Explicit correction judgments after run twenty-one (2026-10-27)

The [review-v3 contract](WORKFLOW_RELIABILITY.md#explicit-correction-judgments-after-run-twenty-one-2026-10-27)
uses keyed semantic judgments and code-derived states, with canonical exports and legacy
v2 reading retained. Full repair text is supplied once; no sources or obligations are
removed. PROJECT_CONTEXT.md, README.md, AGENT_ROLES.md, SOURCE_GROUNDING.md, the testing
guide, project guidance and UI description/types are aligned. The
[validation record](TESTING_AND_RAG.md#explicit-correction-judgments-after-run-twenty-one-2026-10-27)
distinguishes the 147 focused software checks from live failures and analytical quality.
No publication, complete workflow run or UI build.

## Strict Chat transport follow-up (2026-10-27)

The [single-call follow-up](TESTING_AND_RAG.md#single-call-review-follow-up-after-run-twenty-2026-10-27)
adds the transport cardinality setting and content-free rationale diagnostics. Thirty-six
focused checks passed; one live saved-candidate completeness recheck completed with a
revise verdict. Complete workflow quality remains unverified; historical runs are retained.

The [transport checks](TESTING_AND_RAG.md#strict-chat-transport-follow-up-2026-10-27)
cover explicit strict-flag forwarding, three focused adapter checks and two minimal or
synthetic APInex Luna calls without employee data. PROJECT_CONTEXT.md, README.md,
WORKFLOW_RELIABILITY.md and project guidance record the scope and limits. Correction
semantics, both review phases and release gates are unchanged; full analytic quality
and other providers remain unverified. No GitHub publication.

## Current local semantic-review update (2026-10-26)

The [run-eighteen contextual contract](WORKFLOW_RELIABILITY.md#contextual-support-review-fields-after-run-eighteen-2026-10-26)
omits inactive administrative assessment fields from the support tool. Empty defaults
apply only when trusted task lists are empty; active coverage and source/review gates
remain. Actual-schema diagnostics and count-only support_contract metadata are retained.
Tests are aligned but unrun; no API calls or publication. V3 semantic guidance is unchanged.

The [run-seventeen simplification](WORKFLOW_RELIABILITY.md#general-semantic-guidance-after-run-seventeen-2026-10-26)
is current: shared rubric v3 gives general definitions and contextual model judgment.
Case-specific live guidance was removed; v1/v2 histories, full comment input, correction
traceability, all data controls and both reviews remain. Existing fixtures are aligned
without execution. No tests, provider calls, commit or GitHub publication.

The [run-sixteen follow-up](WORKFLOW_RELIABILITY.md#sentiment-and-correction-grounding-after-run-sixteen-2026-10-26)
adds shared versioned definitions in `agents/sentiment_rubric.py`, stored v2 rubric identity,
v1 replay, literal request grounding for new omissions, retained correction excerpts and
full released-group comment/label input to support review. Original's existing challenge
path and ZeroSugar's existing reassessment lifecycle remain responsible for judging
corrections. Counts-only coverage diagnostics and existing privacy/input-size bounds
apply; no new roles, provider settings or budgets. Guides and project context are aligned.
The user requested no tests or GitHub push; validation and live quality remain pending.
Run sixteen is retained evidence for the preceding version.

## Current local review recovery (2026-10-26)

The [recovery contract](WORKFLOW_RELIABILITY.md#review-recovery-after-run-fifteen-2026-10-26)
covers four total drafts with early stopping and unchanged shared budgets, optional
annotation normalization, conservative correction retention, justified
withdrawal of false omissions, and repair-only handoff after incomplete support. Original
still requires both reviews before acceptance. Completeness sees trusted scope/team
context; Cherry/Vanilla retain it from ScopedData. Prompts distinguish examples from
category totals. Context, roles, source contract, READMEs, testing and project guidance
are aligned. Source versions, provider settings, budgets and UI remain unchanged. This
update is local, without GitHub publication or a new live test.

## Current field-diagnostic follow-up (2026-10-26)

The [diagnostic contract](WORKFLOW_RELIABILITY.md#field-error-diagnostics-follow-up-2026-10-26)
updates validation.py, ZeroSugar field checks/repair records and focused regressions.
Current guides/context are aligned; source versions, semantics, roles, UI and provider
settings remain unchanged by this follow-up. Preserve run fourteen as observed evidence.

## Current review/data update (2026-10-26)

The current [workflow contract](WORKFLOW_RELIABILITY.md#review-and-data-contract-update-2026-10-26)
covers origin-neutral role instructions, canonical corrections/reassessment, metric relevance,
phase persistence, versioned partial release, v4/v1-v3 replay, export neutrality and the UI
projection. Update these guides together; historical sections retain their dated meaning.

## Maintenance rules

The 2026-10-26 core audit follow-up is recorded in PROJECT_CONTEXT.md, README.md,
AGENT_ROLES.md, WORKFLOW_RELIABILITY.md and TESTING_AND_RAG.md. It changes pending-review
coverage, Responses output-limit propagation and budgeted Chat request checkpoints;
source rendering, provider configuration and Echo_UI remain unchanged.

1. Verify changed behavior in code/configuration and the relevant result/log before updating claims.
2. Update the context entry and affected operating guides together. Update this map when a
   reference is added, moved, retired or changes purpose; do not copy every implementation
   detail into each file.
3. Preserve historical dates, failed runs and unapproved proposals. Separate implemented,
   observed, locally tested and pending-live behavior. Keep source-bearing reports local.
4. Check relative links, commands and contradictory old instructions. Documentation-only
   updates need content/link review, not live model requests or a new reasoning benchmark.
5. Generated Codex memory, classroom sources, source datasets and license text are not
   automatically edited by project-document maintenance.

The selected 2026-10-23 update is documented in the [current workflow](WORKFLOW_RELIABILITY.md#autonomous-synthesis-and-two-stage-review-2026-10-23), role guide, source contract,
README and testing guide. It retires mandatory deliverable planning and adds separate
completeness/support review calls with metadata-only phase traces. Specialist interfaces,
source replay and the manager UI artifact interface are retained. The full agent suite
passed 242 offline tests; no live provider call was made. GitHub publication is authorized.

Run eleven and its false completeness acceptance are recorded in PROJECT_CONTEXT.md.
For a later authorized repetition keep M14/Q3 2026 and `--profile apinex_test --run-seconds
1000`, preserving earlier artifacts with a fresh output such as
`reports/apinex_prueba_vanilla_12.json`. These offline checks do not certify the next live answer.
The group's manager chat UI remains available locally; natural-language date resolution,
authentication and enterprise writes remain deferred.

Historical documentation review checks: 17 Markdown references and 147 relative file/heading links checked without
errors; documented CLI options checked against `--help`. License text was unchanged.
Only APInex's descriptive status label changed in `connections.json`; endpoints, keys,
model assignments, limits and pacing settings were unchanged. The 207-test result belongs
to the prior implementation verification, not a new run for this documentation update.
